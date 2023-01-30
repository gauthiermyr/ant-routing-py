import asyncio
from random import getrandbits, randint
import networkx as nx
import matplotlib.pyplot as plt

from ant_testing import Node, Payment

def generate_ln_network_from_networkx(network):
    """This will generate a ln network based on a networkx 'network'
    in order to perform an ant search
    """
    node_objects = [Node(node, set(network.neighbors(node))) for node in list(network.nodes)]

    for node in node_objects: node.set_nodes(node_objects)

    return node_objects

def generate_random_ln_network(max_nodes: int = 42, edge_prob: float = 0.08, show_time: int = 10):
    """This will generate a random network
    >>> max_nodes (int): maximum node amount in the network
    >>> edge_prob (float): probability for 2 nodes to be connected
    >>> show_time (int): display the graph, in seconds

    This function returns a list of Node, corresponding to all the nodes 
    in the network
    >>> node_objects (ant_testing.Node[]): list of all the nodes in the network
    """
    tmp = nx.fast_gnp_random_graph(max_nodes, edge_prob)

    subs = list(sorted(nx.connected_components(tmp), key=len, reverse=True))
    g = tmp.subgraph(list(subs[0])).copy()

    g = nx.relabel_nodes(g, { node:i for i,node in enumerate(g.nodes)})

    if show_time > 0:
        nx.draw(g, with_labels=True)
        plt.show(block=False)
        plt.pause(show_time)

    return generate_ln_network_from_networkx(g)
   

def generate_seed():
    """ It generates a random 128 bits seed
    """
    seed = bin(getrandbits(128))[2:].zfill(128) # 128 bits padded
    return seed

# def generate_pheromones_from_seed(seed):
#     if len(seed) != 128:
#         raise Exception("Not a 128 bits seed")

#     phero_alice = str(1) + seed
#     phero_bob = str(0) + seed

#     return (phero_alice, phero_bob)

def start_all_nodes(network):
    """ It will start all the nodes in the network
    """
    for node in network:
        node.start()

def stop_all_nodes(network):
    """ It will stop all the nodes in the network
    """
    for node in network:
        node.stop()

async def get_route(network, alice, bob, amount):
    """ get_route will perform an ant search in the 'network' to find a directed route 
    between 'alice' and 'bob' to do a payment of 'amount'
    """
    if not 0 <= alice < len(network) or not 0 <= bob < len(network) :
        raise Exception("alice or bob are not connected")
    if bob == alice:
        raise Exception("alice and bob is the same node")

    # alice and bob agree on a random 128 bits seed
    seed = generate_seed()

    # pheromone counter, does not start at 0 for privacy reasons
    counter = randint(64,128)

    node_bob = network[bob]
    node_alice = network[alice]

    payment_alice = Payment(
            seed,
            amount,
            False,
            True,
            node_bob,
            node_alice,
            node_bob.maxfees + node_alice.maxfees,
            counter,
            )
    payment_bob = Payment(
            seed,
            amount,
            True,
            False,
            node_bob,
            node_alice,
            node_bob.maxfees + node_alice.maxfees,
            counter,
            )
    
    node_bob.set_payment(payment_bob)
    node_alice.set_payment(payment_alice)


    tasks = []
    for node in network:
        task = asyncio.create_task(node.ant_route())
        tasks.append(task)
        
    await asyncio.gather(*tasks)

async def check_match(network, fromNode, checkTime = 3, stop = True):
    """This function MUST be run in parallel of 'get_route'. It will check every 'checkTime' seconds
    if a match has been created
    in the 'network' for the payement intiated by 'fromNode'
    We can stop all the nodes once found with 'stop'
    """
    found = False
    while(not found):
        if not network[fromNode].payment.match:
            await asyncio.sleep(checkTime)
        else:
            found = True
            if stop:
                stop_all_nodes(network)


def build_route(network, matchId, current, res=[]):
    """Recursive functions that will build a route based on the matches 
    of 'matchId' in the 'network'
    'current' is the node where the match occured and that created de match seed
    """
    next = network[current].match_data[matchId]
    res.append(current)
    if current == next:
        return res
    else:
        return build_route(network, matchId, next, res)
    

async def main():
    """Example of how to perfom an ant search in a random generated graph.
    """

    # 1. we generate a radnom network
    network = generate_random_ln_network(show_time=10)

    # 2. alice wants to pay bob an amount of 1 satoshi
    alice = 2
    bob = 8
    amount = 1
    # 3. Nodes MUST be started to propagates the seed and fin a route
    start_all_nodes(network)
    # 4. In parallel: 
    # - we start the propagation with get_route
    # - we check if a match is created so we can stop the network (for simulation)
    tasks = [asyncio.create_task(get_route(network, alice, bob, amount)), asyncio.create_task(check_match(network, alice))]
    await asyncio.gather(*tasks)

    matchId = network[alice].payment.match.match_id
    doneBy = network[alice].payment.match.from_id

    # 5. A matched seed is created and propagated so we can now build the route
    route = build_route(network, matchId, doneBy)
    
    print('Alice can forward the payment thanks to Bob by using the route', ' > '.join(map(str,route)))


asyncio.run(main())
