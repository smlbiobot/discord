"""
The MIT License (MIT)

Copyright (c) 2018 SML

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

from collections import defaultdict
from collections import namedtuple

import aiohttp
import argparse
import csv
import datetime as dt
import io
import os
import yaml
from addict import Dict
from discord.ext import commands

from cogs.utils.chat_formatting import pagify
from cogs.utils.dataIO import dataIO

PATH = os.path.join("data", "trade")
JSON = os.path.join(PATH, "settings.json")
CARDS_AKA_YML_URL = 'https://raw.githubusercontent.com/smlbiobot/SML-Cogs/master/deck/data/cards_aka.yaml'
CARDS_JSON_URL = 'https://royaleapi.github.io/cr-api-data/json/cards.json'


def nested_dict():
    """Recursively nested defaultdict."""
    return defaultdict(nested_dict)


def clean_tag(tag):
    """clean up tag."""
    if tag is None:
        return None
    t = tag
    if t.startswith('#'):
        t = t[1:]
    t = t.strip()
    t = t.upper()
    return t


TradeItem = namedtuple(
    "TradeItem", [
        "server_id",
        "author_id",
        "give_card",
        "get_card",
        "clan_tag",
        "rarity",
        "timestamp"
    ]
)


class Settings(Dict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self):
        dataIO.save_json(JSON, self.to_dict())

    def check_server(self, server_id):
        if not self[server_id].trades:
            self[server_id].trades = []

    def add_trade_item(self, item: TradeItem):
        """Add trade item."""
        self.check_server(item.server_id)
        self[item.server_id].trades.append(item._asdict())
        self.save()

    def get_trades(self, server_id):
        """Return list of trades"""
        self.check_server(server_id)
        trades = [TradeItem(**item) for item in self[server_id].trades]
        return trades


class Trade:
    """Clash Royale Trading"""

    def __init__(self, bot):
        """Init."""
        self.bot = bot
        self.settings = Settings(dataIO.load_json(JSON))
        self._cards_aka = None
        self._aka_to_card = None
        self._cards_constants = None

    async def get_cards_aka(self):
        if self._cards_aka is None:
            async with aiohttp.ClientSession() as session:
                async with session.get(CARDS_AKA_YML_URL) as resp:
                    data = await resp.read()
                    self._cards_aka = yaml.load(data)
        return self._cards_aka

    async def aka_to_card(self, abbreviation):
        """Go through all abbreviation to find card dict"""
        if self._aka_to_card is None:
            akas = await self.get_cards_aka()
            self._aka_to_card = dict()
            for k, v in akas.items():
                self._aka_to_card[k] = k
                for item in v:
                    self._aka_to_card[item] = k
        return self._aka_to_card.get(abbreviation)

    async def get_cards_constants(self):
        if self._cards_constants is None:
            async with aiohttp.ClientSession() as session:
                async with session.get(CARDS_JSON_URL) as resp:
                    self._cards_constants = await resp.json()
        return self._cards_constants

    async def check_cards(self, cards=None):
        """Make sure all cards have the same rarity."""
        rarities = []
        for c in await self.get_cards_constants():
            for card in cards:
                if c.get('key') == card:
                    rarities.append(c.get('rarity'))
        if len(set(rarities)) == 1:
            return True
        return False

    async def get_rarity(self, card):
        for c in await self.get_cards_constants():
            if c.get('key') == card:
                return c.get('rarity')
        return None

    def get_emoji(self, name):
        """Return emoji by name."""
        name = name.replace('-', '')
        for emoji in self.bot.get_all_emojis():
            if emoji.name == name:
                return '<:{name}:{id}>'.format(name=emoji.name, id=emoji.id)
        return ''

    def get_now_timestamp(self):
        return dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc).timestamp()


    @commands.group(name="trade", pass_context=True)
    async def trade(self, ctx):
        """Clash Royale trades."""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @trade.command(name="add", aliases=['a'], pass_context=True)
    async def add_trade(self, ctx, give: str, get: str, clan_tag: str):
        """Add a trade. Can use card shorthand"""
        server = ctx.message.server
        author = ctx.message.author

        give_card = await self.aka_to_card(give)
        get_card = await self.aka_to_card(get)
        clan_tag = clean_tag(clan_tag)

        rarities = []
        for c in [give_card, get_card]:
            rarities.append(await self.get_rarity(c))

        if len(set(rarities)) != 1:
            await self.bot.say("Rarities does not match.")
            return

        rarity = rarities[0]

        self.settings.add_trade_item(TradeItem(server_id=server.id,
                                               author_id=author.id,
                                               give_card=give_card,
                                               get_card=get_card,
                                               clan_tag=clan_tag,
                                               rarity=rarity,
                                               timestamp=self.get_now_timestamp()))
        self.settings.save()
        await self.bot.say(
            "Give: {give_card}, Get: {get_card}, {clan_tag}, {rarity}".format(
                give_card=give_card,
                get_card=get_card,
                clan_tag=clan_tag,
                rarity=rarity,
            )
        )

    @trade.command(name="import", aliases=['i'], pass_context=True)
    async def import_trade(self, ctx):
        """Import list of trades from CSV file.

        First row is header:
        give,get,clan_tag
        """
        if len(ctx.message.attachments) == 0:
            await self.bot.say(
                "Please attach CSV with this command. "
            )
            return

        attach = ctx.message.attachments[0]
        url = attach["url"]

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.text()

        reader = csv.DictReader(io.StringIO(data))

        async def get_field(row, field, is_card=False, is_clan_tag=False):
            s = row.get(field)
            v = None
            if s is None:
                return None
            s = s.strip()
            if is_card:
                s = s.lower().replace(' ', '-')
                v = await self.aka_to_card(s)
            elif is_clan_tag:
                v = clean_tag(s)
            return v

        trade_items = []

        server = ctx.message.server
        author = ctx.message.author

        for row in reader:
            # normalize string
            give_card = await get_field(row, 'give', is_card=True)
            get_card = await get_field(row, 'get', is_card=True)
            clan_tag = await get_field(row, 'clan_tag', is_clan_tag=True)

            # validate rarities
            rarities = []
            for c in [give_card, get_card]:
                rarities.append(await self.get_rarity(c))

            if len(set(rarities)) != 1:
                await self.bot.say("Rarities does not match for {} and {}".format(give_card, get_card))

            else:
                trade_items.append(
                    TradeItem(
                        server_id=server.id,
                        author_id=author.id,
                        give_card=give_card,
                        get_card=get_card,
                        clan_tag=clan_tag,
                        rarity=rarities[0],
                        timestamp=self.get_now_timestamp()
                    )
                )

        for item in trade_items:
            self.settings.add_trade_item(item)

        self.settings.save()

        o = ["Give: {give_card}, Get: {get_card}, {clan_tag}".format(**item._asdict()) for item in trade_items]
        for page in pagify("\n".join(o)):
            await self.bot.say(page)

    @trade.command(name="list", aliases=['l'], pass_context=True)
    async def list_trades(self, ctx, *args):
        """List trades.

        Optional arguments
        --get,    -g   | get a card, --get nw
        --give,   -g   | give a card --give iwiz
        --rarity, -r   | rarity filter -r epic
        """
        parser = argparse.ArgumentParser()
        parser.add_argument("--get", type=str, help="Get a card")
        parser.add_argument("--give", type=str, help="Give a card")
        parser.add_argument("--rarity", "-r", type=str, help="Rarity filter")

        try:
            pa = parser.parse_args(args)
        except SystemExit:
            await self.bot.send_cmd_help(ctx)
            return

        server = ctx.message.server
        items = self.settings.get_trades(server.id)

        o = []
        now = dt.datetime.utcnow()
        for item in items:
            # skip invalid items
            if not all([item.give_card, item.get_card, item.rarity]):
                continue
            time = dt.datetime.utcfromtimestamp(item.timestamp)
            delta = now - time
            s = delta.total_seconds()
            hours, remainder = divmod(s, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_span = '{: >2}h {: >2}m'.format(int(hours), int(minutes))

            d = item._asdict()
            d.update(dict(
                give_card_emoji=self.get_emoji(item.give_card),
                get_card_emoji=self.get_emoji(item.get_card),
                r=item.rarity[0].upper(),
                s='\u2800',
                time_span=time_span
            ))

            o.append(
                "Give: {give_card_emoji} Get: {get_card_emoji} `{s}{r} #{clan_tag:<9} {time_span}{s}`".format(**d)
            )

        for page in pagify("\n".join(o)):
            await self.bot.say(page)

def check_folder():
    """Check folder."""
    os.makedirs(PATH, exist_ok=True)


def check_file():
    """Check files."""
    if not dataIO.is_valid_json(JSON):
        dataIO.save_json(JSON, {})


def setup(bot):
    """Setup."""
    check_folder()
    check_file()
    n = Trade(bot)
    bot.add_cog(n)
