# -*- coding: utf-8 -*-

"""
The MIT License (MIT)

Copyright (c) 2017 SML

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

import discord
from discord.ext import commands
from .utils import checks
from .utils.dataIO import dataIO
from .general import General
from __main__ import send_cmd_help
import os
import datetime
from PIL import Image
import io

settings_path = "data/deck/settings.json"
crdata_path = "data/deck/clashroyale.json"

class Deck:
    """
    Saves a Clash Royale deck for a user and display them
    """

    def __init__(self, bot):
        self.bot = bot
        self.file_path = settings_path
        self.crdata_path = crdata_path

        self.settings = dataIO.load_json(self.file_path)
        self.crdata = dataIO.load_json(self.crdata_path)

        # init card data
        self.cards = []
        self.cards_abbrev = {}

        for card_key, card_value in self.crdata["Cards"].items():
            self.cards.append(card_key)

            aka_list = card_value["aka"]
            for aka in aka_list:
                self.cards_abbrev[aka] = card_key


        self.card_w = 302
        self.card_h = 363
        self.card_ratio = self.card_w / self.card_h
        self.card_thumb_scale = 0.2
        self.card_thumb_w = int(self.card_w * self.card_thumb_scale)
        self.card_thumb_h = int(self.card_h * self.card_thumb_scale)

    @commands.group(pass_context=True, no_pm=True)
    async def deck(self, ctx):
        """Clash Royale Decks"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @deck.command(name="set", pass_context=True, no_pm=True)
    async def _deck_set(self, ctx, *member_deck:str):
        """
        Set a decklist for the user calling the command

        Example: !deck set archers arrows baby-dragon balloon barbarian-hut barbarians battle-ram bomb-tower
        """

        author = ctx.message.author
        server = ctx.message.server

        self.check_server_settings(server)
        self.check_member_settings(server, author)
        member_deck = [c.lower() for c in member_deck]

        # replace abbreviations
        for i, card in enumerate(member_deck):
            if card in self.cards_abbrev.keys():
                member_deck[i] = self.cards_abbrev[card]

        if len(member_deck) != 8:
            await self.bot.say("Please enter exactly 8 cards")
        elif not set(member_deck) < set(self.cards):
            for card in member_deck:
                if not card in self.cards:
                    await self.bot.say("{} is not a valid card name.".format(card))
            await self.bot.say("**List of cards:** {}".format(", ".join(self.cards))                               )
        else:

            # try:
            # await self.bot.say("Deck saved")
            decks = self.settings["Servers"][server.id]["Members"][author.id]["Decks"]

            # creates sets with decks.values
            decks_sets = [set(d) for d in decks.values()]

            if  set(member_deck) in decks_sets:
                # existing deck
                await self.bot.say("Deck exists already")
            else:
                # new deck
                await self.bot.say("Deck added.")
                deck_key = str(datetime.datetime.utcnow())
                decks[deck_key] = member_deck

                await self.upload_deck_image(ctx, member_deck)

                self.save_settings()

    @deck.command(name="list", pass_context=True, no_pm=True)
    async def deck_list(self, ctx, member:discord.Member=None):
        """List the decks of a user"""

        author = ctx.message.author
        server = ctx.message.server

        if not member:
            member = author

        self.check_server_settings(server)
        self.check_member_settings(server, member)

        decks = self.settings["Servers"][server.id]["Members"][member.id]["Decks"]

        for k, deck in decks.items():
            await self.bot.say(str(deck))

            await self.upload_deck_image(ctx, deck)

    async def upload_deck_image(self, ctx, deck):
        """Upload deck image to the server"""

        deck_image = self.get_deck_image(deck)

        # construct a filename using first three letters of each card
        filename = "deck-{}.png".format("-".join([card[:3] for card in deck]))
        description = "Deck: {}".format(', '.join(deck))

        with io.BytesIO() as f:
            deck_image.save(f, "PNG")
            f.seek(0)
            await ctx.bot.send_file(ctx.message.channel, f, 
                filename=filename, content=description)




    def get_deck_image(self, deck):
        """Construct the deck with Pillow and return image"""

        # PIL.Image.new(mode, size, color=0)
        size = (self.card_thumb_w * 8, self.card_thumb_h)
        out_image = Image.new("RGBA", size)
        # deck_hash = hash(''.join(deck))
        # out_file = "data/deck/img/decks/deck-{}.png".format(deck_hash)

        for i, card in enumerate(deck):
            card_image_file = "data/deck/img/cards/{}.png".format(card)
            card_image = Image.open(card_image_file)
            size = (self.card_thumb_w, self.card_thumb_h)
            card_image.thumbnail(size)
            box = (self.card_thumb_w * i, 0, self.card_thumb_w * (i+1), self.card_thumb_h)
            out_image.paste(card_image, box)

        return out_image


    def check_member_settings(self, server, member):
        """Init member section if necessary"""
        if member.id not in self.settings["Servers"][server.id]["Members"]:
            self.settings["Servers"][server.id]["Members"][member.id] = {
                "MemberID": member.id,
                "MemberDisplayName": member.display_name,
                "Decks": {}}
            self.save_settings()


    def check_server_settings(self, server):
        """Init server data if necessary"""
        if server.id not in self.settings["Servers"]:
            self.settings["Servers"][server.id] = { "ServerName": str(server),
                                                    "ServerID": str(server.id),
                                                    "Members": {} }
            self.save_settings()

    def save_settings(self):
        """Saves data to settings file"""
        dataIO.save_json(self.file_path, self.settings)

def check_folder():
    folders = ["data/deck",
               "data/deck/img",
               "data/deck/img/cards"]
    for f in folders:
        if not os.path.exists(f):
            print("Creating {} folder".format(f))
            os.makedirs(f)

def check_file():
    settings = {
        "Cards": [],
        "Servers": {},
        "Decks": {}
    }
    f = settings_path
    if not dataIO.is_valid_json(f):
        print("Creating default deck settings.json...")
        dataIO.save_json(f, settings)

def setup(bot):
    check_folder()
    check_file()
    n = Deck(bot)
    bot.add_cog(n)


"""  
Bot commands for debugging



http://statsroyale.com/profile/C0G20PR2
http://statsroyale.com/profile/82P9CLC8
http://statsroyale.com/profile/8L9L9GL      
!deck set archers arrows baby-dragon balloon barbarian-hut barbarians battle-ram bomb-tower
!deck set mm bbd loon bt is fs gs lh
!deck set bbd mm loon bt is fs gs lh
!deck set lh mm loon it is fs gs gb
!deck set archers ARROWS baby-dragon BALLOON barbarian-hut barbarians battle-ram bomb-tower
!deck set dark-prince dart-goblin electro-wizard elite-barbarians elixir-collector executioner fire-spirits fireball
!deck set dark-prince dart-goblin2 electro-wizard elite-barbarians2 elixir-collector executioner fire-spirits fireball
dark-prince dart-goblin electro-wizard elite-barbarians elixir-collector executioner fire-spirits
"""
    