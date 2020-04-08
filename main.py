import discord
import boto3.dynamodb
from datetime import timedelta, datetime
from pytz import timezone
from boto3.dynamodb.conditions import Key

dynamo_client = boto3.client('dynamodb',
                      region_name='us-east-2',
                      aws_access_key_id = open("dynamo_accesskey.txt", 'r').read(),
                      aws_secret_access_key = open("dynamo_secret.txt", 'r').read())

resource = boto3.resource('dynamodb',
                      region_name='us-east-2',
                      aws_access_key_id = open("dynamo_accesskey.txt", 'r').read(),
                      aws_secret_access_key = open("dynamo_secret.txt", 'r').read())

table = resource.Table("stalks")


client = discord.Client()


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('!turnip'):
        fmt = "%Y-%m-%d %H:%M:%S %Z%z"
        split = message.content.split()
        if len(split) == 1:
            return
        else:
            est = message.created_at.astimezone(timezone("America/New_York")) - timedelta(hours=4)
            time_of_day = ""
            if(est.hour < 12):
                time_of_day = "morning"
            else:
                time_of_day = "afternoon"
            day_of_week = est.strftime('%A').lower()
            username = message.author.name
            price = int(split[1])

            table.put_item(
                Item={
                    "day_of_week": day_of_week,
                    "username": username,
                    "time_of_day": time_of_day,
                    "price": price
                }
            )

            await message.add_reaction("✅")

    if message.content.startswith('!prices'):
        est = message.created_at.astimezone(timezone("America/New_York")) - timedelta(hours=4)
        day_of_week = est.strftime('%A').lower()
        time_of_day = ''
        if (est.hour < 12):
            time_of_day = "morning"
        else:
            time_of_day = "afternoon"
        response = table.query(KeyConditionExpression=Key("day_of_week").eq(day_of_week))
        max_price = 0
        max_user = ""

        for r in response["Items"]:
            if(r["price"] > max_price and r['time_of_day'] == time_of_day):
                max_price = r["price"]
                max_user = r['username']

        res = "The highest turnip prices right now are " + str(max_price) + " bells from " + max_user
        await message.channel.send(res)

token = open("token.txt", 'r')

client.run(token.read())
