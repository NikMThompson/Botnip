import discord
import boto3.dynamodb
from boto3.dynamodb.conditions import Key

dynamo_client = boto3.client('dynamodb',
                      region_name='us-east-2',
                      aws_access_key_id = open("dynamo_accesskey.txt", 'r').read(),
                      aws_secret_access_key = open("dynamo_secret.txt", 'r').read())

client = discord.Client()


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('!turnip'):
        await message.channel.send('Hello!')


token = open("token.txt", 'r')

client.run(token.read())
