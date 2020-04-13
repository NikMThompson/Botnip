import discord
import boto3.dynamodb
from pytz import timezone
from boto3.dynamodb.conditions import Key
import time

dynamo_client = boto3.client('dynamodb',
                             region_name='us-east-2',
                             aws_access_key_id=open("dynamo_accesskey.txt", 'r').read(),
                             aws_secret_access_key=open("dynamo_secret.txt", 'r').read())

resource = boto3.resource('dynamodb',
                          region_name='us-east-2',
                          aws_access_key_id=open("dynamo_accesskey.txt", 'r').read(),
                          aws_secret_access_key=open("dynamo_secret.txt", 'r').read())

table = resource.Table("stalks")

dodo_code = None

client = discord.Client()


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    global dodo_code
    dodo_code = None


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

    for r in response["Items"]:
        if r["price"] > max_price and r['time_of_day'] == time_of_day:
            max_price = r["price"]
            max_user = r['username']

    if max_price == 0:
        return {'username': 'no one', 'price': "0"}

    return {"username": max_user, "price": max_price}


async def get_lowest_price(message):
    est = message.created_at.astimezone(timezone("America/New_York"))
    day_of_week = est.strftime('%A').lower()
    response = table.query(KeyConditionExpression=Key("day_of_week").eq(day_of_week))
    lowest_price = 999
    lowest_user = ""

    for r in response["Items"]:
        if r["price"] < lowest_price:
            lowest_price = r["price"]
            lowest_user = r['username']

    if lowest_price == 999:
        return {'username': 'no one', 'price': "999"}

    return {"username": lowest_user, "price": lowest_price}


async def create_table():
    try:
        dynamo_client.create_table(
            TableName='stalksTest',
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
        time.sleep(10)
    except dynamo_client.exceptions.ResourceInUseException:
        pass


async def delete_table():
    dynamo_client.delete_table(TableName="stalks")
    time.sleep(10)


async def sunday_cleanup(message):
    est = message.created_at.astimezone(timezone("America/New_York"))
    day_of_week = est.strftime('%A').lower()
    if day_of_week == 'sunday':
        response = table.query(KeyConditionExpression=Key("day_of_week").eq('saturday'))
        if response["Count"] > 0:
            print("cleaning up")
            await message.channel.send("Cleaning up last week's sales, one minute")
            await delete_table()
            await create_table()
        else:
            pass
    else:
        pass


@client.event
async def on_message(message):
    global dodo_code

    if message.author == client.user:
        return

    await sunday_cleanup(message)

    if message.content.startswith('!help'):
        await message.channel.send("use !turnip XXX to set your prices for the current time \n"
                                   "use !prices to get the highest price and user with them \n"
                                   "use !setdodo to set the dodocode to get to your island but it only works if you have the highest current price \n"
                                   "use !getdodo to get the dodocode to the island with the highest price, just remember it might be expired \n"
                                   "use !cleardodo to clear the dodo code if you set it and need to set a new one")

    if message.content.startswith('!turnip'):
        split = message.content.split()
        if len(split) == 1:
            return
        else:
            est = message.created_at.astimezone(timezone("America/New_York"))
            if est.hour < 12:
                time_of_day = "morning"
            else:
                time_of_day = "afternoon"
            day_of_week = est.strftime('%A').lower()
            username = message.author.name
            try:
                price = int(split[1])
            except ValueError:
                print("Invalid price")
                return

            table.put_item(
                Item={
                    "day_of_week": day_of_week,
                    "username_tod": username + "_" + time_of_day,
                    "username": username,
                    "time_of_day": time_of_day,
                    "price": price
                }
            )

            await message.add_reaction("✅")

    if message.content.startswith('!prices'):
        est = message.created_at.astimezone(timezone("America/New_York"))
        day_of_week = est.strftime('%A').lower()

        if day_of_week == 'sunday':
            lowest = await get_lowest_price(message)
            res = "The lowest turnip prices right now are " + str(lowest['price']) + " bells from " + lowest[
                'username']
            await message.channel.send(res)
        else:
            highest = await get_highest_price(message)
            res = "The highest turnip prices right now are " + str(highest['price']) + " bells from " + highest[
                'username']
            await message.channel.send(res)

    if message.content.startswith('!setdodo'):
        est = message.created_at.astimezone(timezone("America/New_York"))
        day_of_week = est.strftime('%A').lower()

        if day_of_week == 'sunday':
            lowest = await get_lowest_price(message)
            lowest_user = lowest['username']
            if message.author.name == lowest_user:
                split = message.content.split()
                if len(split) == 1:
                    return
                else:
                    dodo_code = split[1]
                    await message.add_reaction("✅")
            else:
                await message.channel.send("You must have the lowest turnip prices to set the dodo code")
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

    if message.content.startswith("!getdodo"):
        if dodo_code is None:
            await message.channel.send("The dodo code is not yet set")
        else:
            await message.channel.send(dodo_code)

    if message.content.startswith("!cleardodo"):
        est = message.created_at.astimezone(timezone("America/New_York"))
        day_of_week = est.strftime('%A').lower()

        if day_of_week == 'sunday':
            lowest = await get_lowest_price(message)
            lowest_user = lowest['username']
            if message.author.name == lowest_user:
                dodo_code = None
                await message.add_reaction("✅")
            else:
                await message.channel.send("You must have the lowest turnip prices to clear the dodo code")
        else:
            highest = await get_highest_price(message)
            highest_user = highest['username']
            if message.author.name == highest_user:
                dodo_code = None
                await message.add_reaction("✅")
            else:
                await message.channel.send("You must have the highest turnip prices to clear the dodo code")


token = open("token.txt", 'r')

client.run(token.read())
