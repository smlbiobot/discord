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

import os

import discord
from discord import Message
from discord import Server
from discord.ext import commands
from discord.ext.commands import Context

from __main__ import send_cmd_help
from cogs.utils import checks
from cogs.utils.chat_formatting import box
from cogs.utils.chat_formatting import pagify
from cogs.utils.dataIO import dataIO

try:
    import challonge
except ImportError:
    raise ImportError("Please install the challonge package from https://github.com/russ-/pychallonge.") from None

PATH = os.path.join("data", "challonge")
JSON = os.path.join(PATH, "settings.json")


class Challonge:
    """Challonge API."""

    def __init__(self, bot):
        """Init."""
        self.bot = bot
        self.settings = dataIO.load_json(JSON)

    @commands.group(pass_context=True, no_pm=True)
    @checks.serverowner_or_permissions(manage_server=True)
    async def setchallonge(self, ctx: Context):
        """Set challonge settings.

        http://api.challonge.com/v1"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @setchallonge.command(name="username", pass_context=True)
    async def setchallonge_username(self, ctx: Context, username: str):
        """Set challonge username."""
        if username is None:
            await send_cmd_help(ctx)
            return
        self.settings["API_USERNAME"] = username
        dataIO.save_json(JSON, self.settings)
        await self.bot.say("Challonge API username saved.")
        await self.setchallonge_init()

    @setchallonge.command(name="apikey", pass_context=True)
    async def setchallonge_apikey(self, ctx: Context, apikey: str):
        """Set challonge username."""
        if apikey is None:
            await send_cmd_help(ctx)
            return
        self.settings["API_KEY"] = apikey
        dataIO.save_json(JSON, self.settings)
        await self.bot.say("Challonge API Key saved.")
        await self.setchallonge_init()

    def setchallonge_init(self):
        """Init Challonge api."""
        if not self.check_credentials():
            return False
        challonge.set_credentials(
            self.settings["API_USERNAME"],
            self.settings["API_KEY"])
        return True

    @commands.group(pass_context=True, no_pm=True)
    async def challonge(self, ctx: Context):
        """Challonge API access."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @challonge.command(name="show", pass_context=True)
    async def challonge_show(self, ctx: Context, id):
        """Show the tournament info by id or url."""
        await self.setchallonge_init()
        t = challonge.tournaments.show(id)
        # out = ["{}: {}".format(k, v) for k, v in t.items()]
        # await self.bot.say("\n".join(out))
        await self.bot.say(embed=self.embed_challonge(t))

    @challonge.command(name="create", pass_context=True)
    @checks.serverowner_or_permissions(manage_server=True)
    async def challonge_create(
            self, ctx: Context,
            name, url, tournament_type="single elimination"):
        """Create new tournament."""
        if not self.check_credentials():
            await self.bot.say(
                "Use !setchallonge to set your api credentials.")
            return
        self.setchallonge_init()
        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = {}
        settings = self.settings[server.id]
        if "TOUNAMENTS" not in settings:
            settings["TOURNAMENTS"] = {}
        try:
            t = challonge.tournaments.create(name, url, tournament_type)
            settings["TOURNAMENTS"][t["id"]] = {
                "id": t["id"],
                "name": t["name"],
                "url": t["url"]
            }
            await self.bot.say(embed=self.embed_challonge(t))
            dataIO.save_json(JSON, self.settings)
        except challonge.api.ChallongeException as e:
            await self.bot.say(e)

    def check_credentials(self):
        """Check author has set credentials."""
        if "API_USERNAME" not in self.settings:
            return False
        if "API_KEY" not in self.settings:
            return False
        return True

    def embed_challonge(self, tournament):
        """Return challonge info as Discord embed."""
        em = discord.Embed(
            color=discord.Color(value=int('ff7324', 16)),
            title=tournament["name"])
        fields = [
            ("id", "ID"),
            ("url", "URL"),
            ("description", "Description"),
            ("tournament-type", "Tournament Type"),
            ("started-at", "Started At"),
            ("completed-at", "Completed At"),
            ("full-challonge-url", "URL")
        ]
        for (k, v) in fields:
            em.add_field(
                name=v,
                value=tournament[k])
        return em


def check_folder():
    if not os.path.exists(PATH):
        os.makedirs(PATH)

def check_file():
    defaults = {}
    if not dataIO.is_valid_json(JSON):
        dataIO.save_json(JSON, defaults)

def setup(bot):
    check_folder()
    check_file()
    bot.add_cog(Challonge(bot))