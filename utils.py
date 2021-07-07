import json
import boto3
import logging
import random
import copy
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# #####################################
# ########### Deck Functions ##########
# #####################################


def create_deck():
    suits = ["hearts", "diamonds", "spades", "clubs"]
    vals = [num for num in range(2, 15)]  # 2 to 14 (Ace is 14).
    deck = {}
    card_num = 1

    # Create the deck.
    for suit in suits:
        for val in vals:
            card = suit + "_" + str(val)
            deck[str(card_num)] = card
            card_num += 1

    return deck


def shuffle_deck(deck):
    # Shuffle deck.
    for i in range(len(deck), 1, -1):
        rand = random.randint(1, i)
        deck[str(i)], deck[str(rand)] = deck[str(rand)], deck[str(i)]


def deal_for_players(deck, players):

    # After dealing five card for the table.
    card_index = 6
    for id in players:
        player = players[id]

        # Deal first card
        player["card_1"] = deck[str(card_index)]
        card_index += 1
        # Deal second card
        player["card_2"] = deck[str(card_index)]
        card_index += 1

        # Reset fields
        player["status"] = ""
        player["bet"] = "0"


def print_deck(deck):

    for key in deck:
        print(key, ":   ", deck[key])


# #################################################################################################################


# #####################################
# ########### Data base functions ##########
# #####################################


def get_players(table):
    return table.get_item(Key={'field': "players"})['Item']["players"]  # Get from database.


def get_spectators(table):
    return table.get_item(Key={'field': "spectators"})['Item']["spectators"]  # Get from database.


def get_table_status(table):
   return table.get_item(Key={'field': "table_status"})['Item']  # Get from database.


def get_pots(table):
    return table.get_item(Key={'field': "pots"})['Item']["pots"]  # Get from database.


def calc_pots(pots, players_bets):

    # Players bets are sorted from outside.

    last_pot = len(pots)
    logger.info("pots num:" + str(last_pot))
    # Fill players bets into pots.
    while len(players_bets) != 0:
        last_pot_key = "pot_" + str(last_pot)   # Last pot
        players = sorted([x[0] for x in players_bets])   # Create players.
        bet = players_bets[0][1]   # Get min bet.
        last_pot_players = ["there is no pot yet"]

        if last_pot_key in pots:
            last_pot_players = sorted([i for i in pots[last_pot_key]["players"]])

        logger.info("COMPAREEEEEEEEEEEEEEEEEEE")
        logger.info(players)
        logger.info(last_pot_players)
        
        if last_pot_players == players:
            pots[last_pot_key]["amount"] = str(bet * len(players) + int(pots[last_pot_key]["amount"]))

        else:
            last_pot += 1
            last_pot_key = "pot_" + str(last_pot)
            pots[last_pot_key] = {}
            pots[last_pot_key]["amount"] = str(bet * len(players))
            pots[last_pot_key]["players"] = {key: key for key in players}

        players_bets = [(s, b - bet) for s, b in players_bets if b-bet > 0]


def update_pots(table, pots):
    table.update_item(Key={'field': "pots"},
                      ExpressionAttributeNames={'#b': 'pots'},
                      UpdateExpression="set #b = :count",
                      ExpressionAttributeValues={':count': pots}
                      )


def reset_bets(players):
    for id in players:
        players[id]["bet"] = "0"


def reset_pots(table):
    update_pots(table, {})


def get_next_round_level(round_level):

    if round_level == "pre_flop":
        return "flop"
    if round_level == "flop":
        return "turn"
    if round_level == "turn":
        return "river"

    return "game ended asdddddddddddddddddddddddddddddddddddddddddddd"


def update_players(table, players):
    table.update_item(Key={'field': "players"},
                      ExpressionAttributeNames={'#b': 'players'},
                      UpdateExpression="set #b = :count",
                      ExpressionAttributeValues={':count': players}
                      )
                      
                      
def update_spectators(table, spectators):
    table.update_item(Key={'field': "spectators"},
                      ExpressionAttributeNames={'#b': 'spectators'},
                      UpdateExpression="set #b = :count",
                      ExpressionAttributeValues={':count': spectators}
                      )                     


def update_table_status(table,new_status):

    # Delete old status
    response = table.delete_item(Key={'field': "table_status"})

    # Commit new status
    input = {'field': "table_status", **new_status}
    table.put_item(Item=input)  # Put
# #################################################################################################################

# #############################################
# ########### Controller Helpers ##############
# #############################################


round_levels_mapping = {"pre_flop": 0,
                "flop": 3,
               "turn": 4,
               "river": 5}



def build_client_status(table, players):

    # Get info from data base.
    table_status_info = get_table_status(table)
    # players = get_players(table)

    # Response key:
        # bet: last bet.(for client to know which buttons to use).
        # raise: last raise.(for client to know which buttons to use).
        # cards: cards to show on table.
        # bb,sb : big and small blinds.

    # Decide which cards to display.
    round_level = table_status_info["round_level"]
    cards = table_status_info["cards"]
    to_send_cards = {}
    i = 1
    while i <= round_levels_mapping[round_level]:
        key = "card_" + str(i)
        to_send_cards[key] = cards[key]
        i += 1

    # Prepare pots
    pots = get_pots(table)
    pots_to_send = {}
    for i in range(6):
        pot = "pot_" + str(i)
        if pot in pots:
            pots_to_send[pot] = pots[pot]["amount"]


    response = {"action": "table_status",
                "cards": to_send_cards,
                "bet": table_status_info["bet"],
                "raise": table_status_info["raise"],
                "players": players,
                "dealer_pos": table_status_info["dealer_pos"],
                "round_level": table_status_info["round_level"],
                "turn": table_status_info["turn"],
                "pots": pots_to_send,
                "flag": "sendStatus",
                "status": table_status_info["status"]
                }

    return response


def update_dealer_postion(dealer_pos, players_ids):

    index = players_ids.index(dealer_pos)
    index += 1
    index = index % len(players_ids)
    new_dealer_pos = str(players_ids[index])
    index += 1
    index = index % len(players_ids)
    sb = str(players_ids[index])
    index += 1
    index = index % len(players_ids)
    bb = str(players_ids[index])
    index += 1
    index = index % len(players_ids)
    turn = str(players_ids[index])

    return new_dealer_pos, sb, bb, turn


def broadcast(table, status):

    URL = "https://ea17g2kd0h.execute-api.eu-west-1.amazonaws.com/test/"  # URL of out API Gateway.
    client = boto3.client("apigatewaymanagementapi", endpoint_url=URL)  # Our server as a "client".

    players = get_players(table)
    spectators = get_spectators(table)

    client_status = build_client_status(table, players)
    logger.info(client_status)

    temp_players = copy.deepcopy(players)


    if status != "winning":
        logger.info("entered loop")
        for id in players:
            temp_players[id]["card_1"] = "0" if players[id]["card_1"] != "" else ""
            temp_players[id]["card_2"] = "0" if players[id]["card_2"] != "" else ""


    client_status["players"] = temp_players

    # Send to all spectators.
    for id in spectators:
        connection_id = spectators[id]
        client_status["is_player"] = "0"
        client.post_to_connection(ConnectionId=connection_id, Data=json.dumps(client_status))

    # Send to all players.
    for id in players:
        # Save cards (not really cards, but "" or "0")
        card_1 = copy.copy(temp_players[id]["card_1"])
        card_2 = copy.copy(temp_players[id]["card_2"])

        # Show real cards for the current player.
        temp_players[id]["card_1"] = players[id]["card_1"]
        temp_players[id]["card_2"] = players[id]["card_2"]
        client_status["is_player"] = id

        # client_status["players"] = temp_players

        logger.info("card 1 card 2")
        logger.info(card_1)

        # Send status
        connection_id = players[id]["connection_id"]
        logger.info("post to client")
        logger.info(client_status)
        client.post_to_connection(ConnectionId=connection_id, Data=json.dumps(client_status))

        # Hide cards
        temp_players[id]["card_1"] = card_1
        temp_players[id]["card_2"] = card_2


def get_next_turn(players, curr_turn):

    playing_players = [int(i) for i in players if (players[i]["status"] != "fold" and players[i]["status"] != "all_in")]
    playing_players = sorted(playing_players)
    curr_index = playing_players.index(int(curr_turn))
    next_index = (curr_index+1)% len(playing_players)
    return str(playing_players[next_index])


def get_active_players(players):
    return {player:players[player] for player in players if players[player]["status"] != "fold"}


def send_refreshed_status(table, players, seat, connection_id):

    URL = "https://ea17g2kd0h.execute-api.eu-west-1.amazonaws.com/test/"  # URL of out API Gateway.
    client = boto3.client("apigatewaymanagementapi", endpoint_url=URL)  # Our server as a "client".


    client_status = build_client_status(table, players)

    temp_players = copy.deepcopy(players)

    # Hide temp players' cards
    for id in players:
        temp_players[id]["card_1"] = "0" if players[id]["card_1"] != "" else ""
        temp_players[id]["card_2"] = "0" if players[id]["card_2"] != "" else ""

    # Check if the client is a player? (spectatos means seat == 0).
    if seat != "0":
        # Flip cards for the players
        temp_players[seat]["card_1"] = players[seat]["card_1"]
        temp_players[seat]["card_2"] = players[seat]["card_2"]

    # Update cards
    client_status["players"] = temp_players
    client_status["is_player"] = seat

    logger.info("connection id")
    logger.info(connection_id)
    # Send status to the client.
    client.post_to_connection(ConnectionId=connection_id, Data=json.dumps(client_status))



# #############################################
# ########### Choose winner section ##############
# #############################################

"""
File: detector.py
Author: dave
Github: https://github.com/davidus27
Description: Library for easier detection of all existing hand values of players.
"""

"""
All possible hand values checkers:

    0) Highcard: Simple value of the card.

    1) Pair: Two cards with same value.

    2) Two pairs: Two different pairs.

    3) Three of a Kind: Three cards with the same value

    4) Straight: Sequence of five cards in increasing value (Ace can precede two and follow up King)

    5) Flush: Five cards of the same suit

    6) Full House: Combination of three of a kind and a pair

    7) Four of a kind: Four cards of the same value

    8) Straight flush: Straight of the same suit

    9) Royal Flush: Straight flush from Ten to Ace


The value of hand will get number based on the sequence above
    (Pair will get 1, Straight will get 4 and so on) 

Highcard will enumerate decimal places so if two players will have same hand the higher cards will win.

Card format:
    (number, color)
"""


def createHistogram(cards):
    """
    Creates histogram of hole and community cards

    :cards: TODO
    :returns: histogramictionary of used cards

    """
    histogram = {}
    for i in cards:
        if i[0] not in histogram:
            histogram[i[0]] = 0
        else:
            histogram[i[0]] += 1

    return histogram


def find(cards, value):
    """
    Returns list of cards with same value
    :cards: haystack
    :value: needle
    :returns: needle(s)

    """
    pack = []
    for i in cards:
        if i[0] is value:
            pack.append(i)
    return pack


#  not working correctly change it!:  <23-08-19, yourname> #
def highCard(cards):
    """
    Finds the high value of cards. From the biggest card to the lowest it increments the decimal place.

    :cards: TODO
    :returns: float

    """
    value = 0.0
    for index, card in enumerate(cards):
        value += 0.01 ** (index + 1) * (cardsOrder.index(card[0]))
    return value


#  override without histogram:  <23-08-19, yourname> #
def pair(histogram, cards):
    """
    Checks if the dictionary has ONE pair
    Calculates cardValue of hand
    :returns: value of hanhistogram
    """
    for i in histogram:
        if histogram[i] == 1:
            return find(cards, i)

    return False


def twoPairs(histogram, cards):
    """
    Two different pairs
    :returns: TODO

    """
    count = 0
    pack = []
    for i in histogram:
        if histogram[i] == 1:
            pack.append(find(cards, i))
    return pack if len(pack) == 2 else False


def threeOfKind(histogram, cards):
    """
    Finds Three of a kind (Three histogram with same value)
    :histogram: dictionary of hole and community histogram
    :returns: boolean

    """
    for i in histogram:
        if histogram[i] == 2:
            return find(cards, i)
    return False


def fourOfKind(histogram, cards):
    """
    Finds Four of a kind (four histogram with same value)

    :histogram: dictionary
    :returns: boolean

    """
    for i in histogram:
        if histogram[i] == 3:
            return find(cards, i)
    return False


def straight(cards):
    """
    Five cards in order
    :returns: TODO

    """
    pack = []
    for index, card in enumerate(cards):
        if len(pack) == 4:
            pack.append(card)
            return pack
        control = cardsOrder.index(card[0]) - cardsOrder.index(cards[index + 1][0])
        if control == 1:
            pack.append(card)
        elif control == 0:
            continue
        else:
            return False


def sortCards(cards):
    """
    Sort cards from highest based on values

    :cards: TODO
    :returns: TODO

    """
    return sorted(cards, key=lambda a: (cardsOrder.index(a[0]), a[1]), reverse=True)


def flush(cards):
    """
    Five cards of the same suit
    :returns: TODO

    """
    # it will lookup the biggest flush in cards
    suits = ["Spades", "Clubs", "Diamonds", "Hearts"]

    for suit in suits:
        pack = []
        for card in cards:
            if card[1] == suit:
                pack.append(card)
        if len(pack) >= 5:
            return pack
    return False
    """
    for i in suits:
        pack=[]
        for j in cards:
            if j[1] is i:
                pack.append(j)
            if len(pack) >= 5:
                return pack
    return False
    """


def fullHouse(histogram, cards):
    """
    A pair and 3 of a kind
    :returns: TODO

    """
    pack = []
    for i in histogram:
        if histogram[i] == 1 or histogram[i] == 2:
            pack += find(cards, i)
    return pack if len(pack) == 5 else False


def straightFlush(cards):
    """
    Straight and flush
    :returns: TODO

    """
    # not functioning properly:  <25-07-19, dave> #
    flushCards = flush(cards)
    straightCards = straight(cards)
    if straightCards == flushCards:
        return straightCards
    return False


def royalFlush(cards):
    """
    The highest cards on hand.
    all of the same color: 10,jack,queen, king, ace
    :returns: TODO

    """
    royal = [10, "Jack", "Queen", "King", "Ace"]
    flushCards = flush(cards)
    if flushCards:
        for i in flushCards:
            if i[0] not in royal:
                return False
        return flushCards
    return False


def findHandValue(cards):
    """
    Goes through the list of possible hands to find best one from top to the bottom

    :player: TODO
    :returns: float/int hand value of the player

    """
    histogram = createHistogram(cards)
    options = [royalFlush(cards),
               straightFlush(cards),
               fourOfKind(histogram, cards),
               fullHouse(histogram, cards),
               flush(cards),
               threeOfKind(histogram, cards),
               twoPairs(histogram, cards),
               pair(histogram, cards), ]

    for index, option in enumerate(options):
        if option:
            # royalflush has lowest index so we invert values
            # bigger number means better hand
            return (8 - index) + highCard(cards)
    return highCard(cards)


map_suit_format = {"diamonds" : "Diamonds",
                    "clubs": "Clubs",
                    "spades": "Spades",
                    "hearts": "Hearts"}

map_value_format = {"2": 2, "3": 3, "4":4, "5":5, "6":6,
                    "7":7, "8":8,"9":9,"10":10,"11":"Jack",
                    "12":"Queen", "13":"King","14":"Ace"}

cardsOrder = [2,3,4,5,6,7,8,9,10, "Jack", "Queen" , "King", "Ace"]


# Combines the 5 table cards with the player two cards.
# Convert to another cards format.
def combine_cards(card_1, card_2, cards):
    combined = [cards[key] for key in cards]
    combined.append(card_1)
    combined.append(card_2)

    result = []
    for card in combined:
        info = card.split("_")
        result.append((map_value_format[info[1]], map_suit_format[info[0]]) )

    return result



def calculate_scores(players, cards):

    for id in players:
        card_1 = players[id]["card_1"]
        card_2 = players[id]["card_2"]
        combined_cards = combine_cards(card_1, card_2, cards)
        combined_cards = sorted(combined_cards, key = lambda a: (cardsOrder.index(a[0]), a[1]), reverse=True)
        players[id]["hand_score"] = findHandValue(combined_cards)

    return players


# Takes info of all players, and table cards.
def calc_winnings(active_players, cards, pots, players):
    """
    returns the winning player or winning players in case of more than one winner.
    """


    # Calculate hand score for everyone, write the score in "hand_value" field.
    calculate_scores(active_players, cards)

    logger.info(active_players)

    # For every pot find the active players choose the best score and divide the pot amount.
    for pot in pots:
        participantes = pots[pot]["players"]

        max_score = max([(active_players[p]["hand_score"]) for p in participantes if p in active_players])
        logger.info(max_score)
        winners = [i for i in active_players if active_players[i]["hand_score"] == max_score]
        slice = int(pots[pot]["amount"]) / len(winners)
        for id in winners:
            players[id]["balance"] = str(int(players[id]["balance"])+ int(slice))

    # Remove hand score field for the players.
    for id in players:
        if "hand_score" in players[id]:
            del players[id]["hand_score"]

    logger.info(players)




