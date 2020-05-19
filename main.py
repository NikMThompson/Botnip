import json
import os
from collections import OrderedDict

import boto3.dynamodb
import discord
from boto3.dynamodb.conditions import Key, Attr
from pytz import timezone

import archipelago

# Create the client using the access key and secret files that should in the root of ths folder
dynamo_client = boto3.client('dynamodb',
                             region_name='us-east-2',
                             aws_access_key_id=open("dynamo_accesskey.txt", 'r').read(),
                             aws_secret_access_key=open("dynamo_secret.txt", 'r').read())
# Create the resource using the access key and secret files that should in the root of ths folder
resource = boto3.resource('dynamodb',
                          region_name='us-east-2',
                          aws_access_key_id=open("dynamo_accesskey.txt", 'r').read(),
                          aws_secret_access_key=open("dynamo_secret.txt", 'r').read())

# The table that will hold the prices information.
# This will be used throughout so you can change the name here to be reflected everywhere
table = resource.Table("stalks")

#  Global dodo code that is shared throughout the bot
dodo_code = None

# The discord client to interact and post to discord
client = discord.Client()


@client.event
# A method that runs when the apps starts up. There is a log that prints out if you run in an interactive mode
# The dodo code is set and reset whenever this runs so if the bot is ever taken off or redeployed it will be reset
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    global dodo_code
    dodo_code = None


# Method to get the highest price in the table for the current day and time period combination
async def get_highest_price(message):
    est = message.created_at.astimezone(timezone("America/New_York"))
    day_of_week = est.strftime('%A').lower()
    if est.hour < 12:
        time_of_day = "morning"
    else:
        time_of_day = "afternoon"
    response = table.query(KeyConditionExpression=Key("day_of_week").eq(day_of_week))
    max_price = 0
    max_user = ""

    # Iterate through the records for the current day of the week and check if the prices are above the current max
    # and the time of day is current. If so then set the max price and user to whatever it is in that record
    for r in response["Items"]:
        if r["price"] > max_price and r['time_of_day'] == time_of_day:
            max_price = r["price"]
            max_user = r['username']

    # if max price after iterating through all the records for the day is still 0 then we can assume no one has put in
    # any prices for the day and return that no one has the highest price
    if max_price == 0:
        return {'username': 'no one', 'price': "0"}

    return {"username": max_user, "price": max_price}


# Get the lowest price for the current day and time slice. This is going to be used for Sundays when we need
# the lowest price instead of the highest
async def get_lowest_price(message):
    est = message.created_at.astimezone(timezone("America/New_York"))
    day_of_week = est.strftime('%A').lower()
    response = table.query(KeyConditionExpression=Key("day_of_week").eq(day_of_week))
    lowest_price = 999
    lowest_user = ""

    # Much like the highest price function we are looping through all the records on the current day but not caring
    # about the time slice. This is because prices only happen once on Sunday so we don't need the check
    for r in response["Items"]:
        if r["price"] < lowest_price:
            lowest_price = r["price"]
            lowest_user = r['username']

    if lowest_price == 999:
        return {'username': 'no one', 'price': "999"}

    return {"username": lowest_user, "price": lowest_price}


# General function to create the table to hold the prices
# The table has two keys, the day_of_week and username_tod. username_tod is concatenation of the username and
# time of day making each record unique in 3 ways. This means that if a user inputs a price in the same day and time
# slice then their record will just be updated.
async def create_table():
    try:
        dynamo_client.create_table(
            TableName=table.name,
            KeySchema=[
                {
                    'AttributeName': 'day_of_week',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'username_tod',
                    'KeyType': 'RANGE'
                }

            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'day_of_week',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'username_tod',
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        # Tables are instantly created and ready to use however the method will return as soon as the table is sent to
        # the 'CREATING' state so this will effectively wait until it is ready to use
        while dynamo_client.describe_table(TableName=table.name)["Table"]["TableStatus"] == "CREATING":
            pass
        return
    # Catch this exception and just continue since we don't need to make the table twice
    except dynamo_client.exceptions.ResourceInUseException:
        pass


# General function to delete our current table. Will be used in the sunday cleanup function later
async def delete_table():
    dynamo_client.delete_table(TableName=table.name)


# Every day we need to reset the dodo code so that it doesn't stick around. Theoretically there can be cases where this
# might be disruptive (highest price user sets dodo code and is using it to invite people over even after shops close)
# but for the purpose of a /turnip/ bot it is helpful since shops close at 10PM
async def daily_clear_dodo(message):
    global dodo_code
    if dodo_code is not None:
        est = message.created_at.astimezone(timezone("America/New_York"))
        response = table.query(KeyConditionExpression=Key("day_of_week").eq(est.strftime('%A').lower()))
        if response["Count"] == 0:
            dodo_code = None
        else:
            return
    else:
        return


# Sunday is the start of a new week in ACNH and turnips are sold again. In order to keep size down this bot only keeps
# a week's worth of data at a time so it is necessary to wipe the table Sunday so that the new week can start fresh
# This function will delete and then rebuild the table on the first message sent in the server (not necessarily related
# to the bot) after 12:00 AM Sunday
async def sunday_cleanup(message):
    est = message.created_at.astimezone(timezone("America/New_York"))
    day_of_week = est.strftime('%A').lower()
    if day_of_week == 'sunday':
        # Don't just blindly delete if it's Sunday, only delete data if it's Sunday and
        # there is data in there from Saturday so we know we have last week's data
        response = table.query(KeyConditionExpression=Key("day_of_week").eq('saturday'))
        if response["Count"] > 0:
            # commenting out this message because I like the functionality of it cleaning the table whenever someone
            # sends a message in any channel after 12:01 AM but don't want it to send the message in random channels
            # await message.channel.send("Cleaning up last week's sales, one minute")
            await delete_table()
            try:
                # Much like when creating tables, deleting tables isn't instant and there are issues trying to create a
                # table with the same name before the other is deleted. This will wait until it's done by checking the
                # status and when an exception is thrown that we can't find the table it will continue
                while dynamo_client.describe_table(TableName=table.name)["Table"]["TableStatus"] == "DELETING":
                    pass
            except dynamo_client.exceptions.ResourceNotFoundException:
                pass
            await create_table()
        else:
            pass
    else:
        pass


# Method to create the json file to be passed to the plotting algorithm for predicting prices over the week
# The json for that needs to be formatted in a specific way so it's a little funky and deeply nested but without
# reworking the way it takes the json it needs to be like this
async def make_json_for_user(message):
    name = str(message.author).split('#')[0]
    response = table.scan(FilterExpression=Attr("username").eq(name))
    outer_json = {}
    islands_json = {}
    name_json = {}
    timeline_json = {}
    # Need this map to sort the records since they aren't stored in logical order in the database but need to
    # be for the json
    convert = {'Sunday_AM': 0, 'Monday_AM': 1, 'Monday_PM': 2, 'Tuesday_AM': 3, 'Tuesday_PM': 4, 'Wednesday_AM': 5,
               'Wednesday_PM': 6, 'Thursday_AM': 7, 'Thursday_PM': 8, 'Friday_AM': 9, 'Friday_PM': 10,
               'Saturday_AM': 11, 'Saturday_PM': 12}

    # Loop through all the records for the user, format the day of the week/time, and add it and the price to
    # the timeline json
    for item in response["Items"]:
        time = 'PM'
        if item["time_of_day"] == 'morning' or item["day_of_week"] == "Sunday":
            time = 'AM'
        key = item["day_of_week"].capitalize() + "_" + time
        timeline_json[key] = int(item["price"])

    # Sort the timeline json based on our map from above
    timeline_json = dict(OrderedDict(sorted(timeline_json.items(), key=lambda i: convert.get(i[0]))))

    # Nest the jsons to get them in the format needed for the algorithm
    name_json["timeline"] = timeline_json
    islands_json[name] = name_json
    outer_json["islands"] = islands_json
    final_json = json.dumps(outer_json)

    # Write the json to a the username of whoever requested the graph
    filename = str(message.author).split('#')[0] + ".json"
    with open(filename, 'w') as outfile:
        outfile.write(str(final_json))
    return response


@client.event
# The beginning of where we will look for messages to the bot
async def on_message(message):
    global dodo_code

    # Disregard any messages from the bot
    if message.author == client.user:
        return

    # Check if it's sunday and we need to clean up before anything else
    await sunday_cleanup(message)
    # Clear the dodo code if needed
    await daily_clear_dodo(message)

    # A help message to display the current commands and what they do
    if message.content == '!help':
        await message.channel.send("use !turnip XXX to set your prices for the current time \n"
                                   "use !prices to get the highest price and user with them \n"
                                   "use !setdodo to set the dodocode to get to your island but it only works if you have the highest current price \n"
                                   "use !getdodo to get the dodocode to the island with the highest price, just remember it might be expired \n"
                                   "use !cleardodo to clear the dodo code if you set it and need to set a new one \n"
                                   "use !stonks to get a forecast of your prices for the week. If it finds no models that match your pattern it'll return blank.  Still a work in progress!")

    # Setting prices message
    if message.content.startswith('!turnip'):
        split = message.content.split()
        # People kept doing !turnips so it takes both
        if len(split) == 1 or (split[0] != '!turnip' and split[0] != '!turnips'):
            return
        else:
            est = message.created_at.astimezone(timezone("America/New_York"))
            if est.hour < 12:
                time_of_day = "morning"
            else:
                time_of_day = "afternoon"
            day_of_week = est.strftime('%A').lower()
            username = message.author.name

            # If someone tries to be funny and put something that isn't a price this will fail and just stop
            # That said there aren't any guardrails on how high or how low a price someone puts so that's all in best
            # faith on the users to not abuse
            try:
                price = int(split[1])
            except ValueError:
                print("Invalid price")
                return

            # Put the record in the table
            table.put_item(
                Item={
                    "day_of_week": day_of_week,
                    "username_tod": username + "_" + time_of_day,
                    "username": username,
                    "time_of_day": time_of_day,
                    "price": price
                }
            )

            # React to the message so the user knows that they have had their price recorded
            await message.add_reaction("✅")

    # Get the highest (or on Sunday, lowest) prices currently
    if message.content == '!prices':
        est = message.created_at.astimezone(timezone("America/New_York"))
        day_of_week = est.strftime('%A').lower()

        # If it's Sunday get the lowest price
        if day_of_week == 'sunday':
            lowest = await get_lowest_price(message)
            res = "The lowest turnip prices right now are " + str(lowest['price']) + " bells from " + lowest[
                'username']
            await message.channel.send(res)
        # Otherwise get the highest
        else:
            highest = await get_highest_price(message)
            res = "The highest turnip prices right now are " + str(highest['price']) + " bells from " + highest[
                'username']
            await message.channel.send(res)

    # Set the dodo code, only works if you have the highest price currently
    if message.content.startswith('!setdodo'):
        est = message.created_at.astimezone(timezone("America/New_York"))
        day_of_week = est.strftime('%A').lower()

        # If it's Sunday we need to check who has the lowest prices
        if day_of_week == 'sunday':
            lowest = await get_lowest_price(message)
            lowest_user = lowest['username']
            # If the person who sent the message has the lowest prices then continue in
            if message.author.name == lowest_user:
                split = message.content.split()
                if len(split) == 1 or split[0] != '!setdodo':
                    return
                else:
                    dodo_code = split[1]
                    await message.add_reaction("✅")
            else:
                # If they don't have the lowest prices then let them know so they don't keep trying
                await message.channel.send("You must have the lowest turnip prices to set the dodo code")
        # If it isn't Sunday then do the same thing but with the highest prices instead of lowest
        else:
            highest = await get_highest_price(message)
            highest_user = highest['username']
            if message.author.name == highest_user:
                split = message.content.split()
                if len(split) == 1:
                    return
                else:
                    dodo_code = split[1]
                    await message.add_reaction("✅")
            else:
                await message.channel.send("You must have the highest turnip prices to set the dodo code")

    # Get the current dodo code, anyone can request it and if it isn't set it'll respond in kind
    if message.content == "!getdodo":
        if dodo_code is None:
            await message.channel.send("The dodo code is not yet set")
        else:
            await message.channel.send(dodo_code)

    # Clear the dodo code, only works if you have the highest prices just like with setting it
    # Useful if you are closing down and don't want to let people think the code is still active
    if message.content == "!cleardodo":
        est = message.created_at.astimezone(timezone("America/New_York"))
        day_of_week = est.strftime('%A').lower()

        # If it's sunday use the lowest prices
        if day_of_week == 'sunday':
            lowest = await get_lowest_price(message)
            lowest_user = lowest['username']
            if message.author.name == lowest_user:
                dodo_code = None
                await message.add_reaction("✅")
            else:
                await message.channel.send("You must have the lowest turnip prices to clear the dodo code")
        # Any other day than Sunday use the highest prices
        else:
            highest = await get_highest_price(message)
            highest_user = highest['username']
            if message.author.name == highest_user:
                dodo_code = None
                await message.add_reaction("✅")
            else:
                await message.channel.send("You must have the highest turnip prices to clear the dodo code")

    # Get a forecast for the week with the current data for the user
    if message.content.startswith("!stonks"):
        # Make the json with their current information
        await make_json_for_user(message)
        filename = str(message.author).split('#')[0] + ".json"
        # And send it to the algorithm
        arch = archipelago.Archipelago.load_file(filename)
        arch.plot()

        # Remove the json file so it doesn't clutter up the instance memory
        os.remove(filename)
        filename = str(message.author).split('#')[0] + ".png"
        # Send the image with the graph
        await message.channel.send(file=discord.File(filename))
        # And then remove it
        os.remove(filename)


# Get the token for the discord application from the token file in the root directory
token = open("token.txt", 'r')

# Start the bot
client.run(token.read())
