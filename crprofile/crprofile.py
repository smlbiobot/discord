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

import asyncio
import aiohttp
import inflect
import datetime as dt
import itertools
import json
import os
from collections import defaultdict
from datetime import timedelta
from enum import Enum
from random import choice

import discord
from __main__ import send_cmd_help
from discord.ext import commands

from cogs.utils import checks
from cogs.utils.chat_formatting import inline, box
from cogs.utils.dataIO import dataIO

PATH = os.path.join("data", "crprofile")
PATH_PLAYERS = os.path.join(PATH, "players")
JSON = os.path.join(PATH, "settings.json")
BADGES_JSON = os.path.join(PATH, "badges.json")

DATA_UPDATE_INTERVAL = timedelta(minutes=30).seconds

API_FETCH_TIMEOUT = 5

BOTCOMMANDER_ROLES = ["Bot Commander"]

CREDITS = 'Harmiox + SML'


def grouper(n, iterable, fillvalue=None):
    """Group lists into lists of items.

    grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"""
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)


def nested_dict():
    """Recursively nested defaultdict."""
    return defaultdict(nested_dict)


def random_discord_color():
    """Return random color as an integer."""
    color = ''.join([choice('0123456789ABCDEF') for x in range(6)])
    color = int(color, 16)
    return discord.Color(value=color)


class SCTag:
    """SuperCell tags."""

    TAG_CHARACTERS = list("0289PYLQGRJCUV")

    def __init__(self, tag):
        """Init.

        Remove # if found.
        Convert to uppercase.
        """
        if tag is not None:
            if tag.startswith('#'):
                tag = tag[:1]
            tag = tag.upper()
        self._tag = tag

    @property
    def tag(self):
        """Return tag as str."""
        return self._tag

    @property
    def valid(self):
        """Return true if tag is valid."""
        for c in self.tag:
            if c not in self.TAG_CHARACTERS:
                return False
        return True

    @property
    def invalid_chars(self):
        """Return list of invalid characters."""
        invalids = []
        for c in self.tag:
            if c not in self.TAG_CHARACTERS:
                invalids.append(c)
        return invalids

    @property
    def invalid_error_msg(self):
        """Error message to show if invalid."""
        return (
            'The tag you have entered is not valid. \n'
            'List of invalid characters in your tag: {}\n'
            'List of valid characters for tags: {}'.format(
                ', '.join(self.invalid_chars),
                ', '.join(self.TAG_CHARACTERS)
            ))


class CRArenaModel:
    """Clash Royale arenas."""

    def __init__(self, **kwargs):
        """Init.

        Keyword Args:
            Name (str)
            TID (str)
            TIDText (str)
            SubtitleTID (str)
            SubtitleTIDText (str)
            Arena (int)
            ChestArena (str)
            TvArena (str)
            IsInUse (bool)
            TrainingCamp (bool)
            PVEArena (str)
            TrophyLimit (int)
            DemoteTrophyLimit (int)
            SeasonTrophyReset (str)
            ChestRewardMultiplier (int)
            ChestShopPriceMultiplier (int)
            RequestSize (int)
            MaxDonationCountCommon (int)
            MaxDonationCountRare (int)
            MaxDonationCountEpic (int)
            IconSWF (str)
            IconExportName (str)
            MainMenuIconExportName (str)
            SmallIconExportName (str)
            MatchmakingMinTrophyDelta (int)
            MatchmakingMaxTrophyDelta (int)
            MatchmakingMaxSeconds (int)
            PvpLocation (str)
            TeamVsTeamLocation (str)
            DailyDonationCapacityLimit (int)
            BattleRewardGold (str)
            ReleaseDate (str)
        """
        self.__dict__.update(kwargs)


class CRPlayerModel:
    """Clash Royale arenas."""

    def __init__(self, is_cache=False, **kwargs):
        """Init.

        Keyword Args:
            username (str)
            tag (str)
            trophies {}
                current (int)
                legend (int)
                highest (int)
            level (int)
            experience (int)
            rank (int)
            clan {}
                name (str)
                tag (str)
                role (str)
                badge_url (str, url)
                badge_id (int)
            chests {}
                order_index (int)
                count (int)
                super_magical (int)
                legendary (int)
                epic (int)
                index (int)
                cycle [str]
                fullcycle [str]
            gold (int)
            gems (int)
            wins (int)
            losses (int)
            draws (int)
            three_crown_wins (int)
            cards_found (int)
            favorite_card_id (int)
            favorite_card (str)
            deck []
                id (int)
                level (int)
                Unk1 (int)
                Count (int)
                Unk2 (int)
                Unk3 (int)
                New (int)
                name (str)
            areana_url (str, url)
        """
        self.__dict__.update(kwargs)
        self.is_cache = is_cache

    @property
    def xp(self):
        """Experience in current / total format."""
        xp_levels = [
            "0",
            "20",
            "50",
            "100",
            "200",
            "400",
            "1000",
            "2000",
            "5000",
            "10000",
            "30000",
            "40000",
            "80000",
            "MAX"
        ]
        current = 'MAX'
        total = 'MAX'
        if str(self.experience).isdigit():
            current = '{:,}'.format(int(self.experience))
        if xp_levels[self.level].isdigit():
            total = '{:,}'.format(int(xp_levels[self.level]))
        return '{} / {}'.format(current, total)

    @property
    def clan_name(self):
        """Clan name."""
        return self.clan["name"]

    @property
    def clan_tag(self):
        """Clan tag."""
        return self.clan["tag"]

    @property
    def clan_role(self):
        """Clan role."""
        return self.clan["role"]

    @property
    def clan_badge_url(self):
        """Clan badge url."""
        badges = dataIO.load_json(BADGES_JSON)
        key = str(self.clan["badge_id"] - 1 + 16000000)
        return 'https://smlbiobot.github.io/img/emblems/{}.png'.format(badges[key])

    @property
    def trophy_current(self):
        """Current trophies."""
        return self.trophies["current"]

    @property
    def trophy_highest(self):
        """Personal best."""
        return self.trophies["highest"]

    @property
    def trophy_legendary(self):
        """Legendary trophies."""
        return self.trophies["legend"]

    @property
    def chest_magical_index(self):
        """First index of magical chest"""
        return self.chests["fullcycle"].index("Magic")

    @property
    def chest_giant_index(self):
        """First index of magical chest"""
        return self.chests["fullcycle"].index("Giant")

    @property
    def win_ratio(self):
        """Win ratio."""
        return '{0:.3f}%'.format(
            (self.wins + self.draws * 0.5) / (self.wins + self.draws + self.losses) * 100)

    @property
    def arena(self):
        """League. Can be either Arena or league."""
        arenas = dataIO.load_json(os.path.join(PATH, 'arenas.json'))
        arenas = [CRArenaModel(**a) for a in arenas]
        arenas = sorted(arenas, key=lambda x: x.TrophyLimit, reverse=True)

        result = None
        for arena in arenas:
            if self.trophy_current >= arena.TrophyLimit:
                result = arena
                break

        return result

    @property
    def arena_text(self):
        """Arena text."""
        return self.arena.TIDText

    @property
    def arena_subtitle(self):
        """Arena subtitle"""
        return self.arena.SubtitleTIDText

    @property
    def league(self):
        """League (int)."""
        league = max(self.arena.Arena - 11, 0)
        return league

    def arena_emoji(self, bot):
        if self.league > 0:
            name = 'league{}'.format(self.league)
        else:
            name = 'arena{}'.format(self.arena.Arena)
        for server in bot.servers:
            for emoji in server.emojis:
                if emoji.name == name:
                    return '<:{}:{}>'.format(emoji.name, emoji.id)
        return ''

class ServerModel:
    """Discord server data model.

    Sets per-server settings since the bot can be run on multiple servers.
    """
    DEFAULTS = {
        "players": {}
    }

    def __init__(self, data=None):
        """Init."""
        if data is None:
            data = self.DEFAULTS
        self.settings = data


class Settings:
    """Cog settings.

    Functionally the CRClan cog model.
    """

    DEFAULTS = {
        "profile_api_url": {},
        "servers": {},
    }

    SERVER_DEFAULTS = {
        "show_resources": False,
        "players": {}
    }

    def __init__(self, bot, filepath):
        """Init."""
        self.bot = bot
        self.filepath = filepath
        self.settings = nested_dict()
        self.settings.update(dataIO.load_json(filepath))

        # arenas
        arenas = dataIO.load_json(os.path.join(PATH, 'arenas.json'))
        self.arenas = [CRArenaModel(**a) for a in arenas]
        self.arenas = sorted(self.arenas, key=lambda x: x.TrophyLimit, reverse=True)

    def init_server(self, server):
        """Initialized server settings.

        This will wipe all clan data and player data.
        """
        self.settings["servers"][server.id] = self.SERVER_DEFAULTS
        self.save()

    def init_players(self, server):
        """Initialized clan settings."""
        self.settings["servers"][server.id]["players"] = {}
        self.save()

    def check_server(self, server):
        """Make sure server exists in settings."""
        if server.id not in self.settings["servers"]:
            self.settings["servers"][server.id] = self.SERVER_DEFAULTS
        self.save()

    def get_players(self, server):
        """CR Players settings by server."""
        return self.settings["servers"][server.id]["players"]

    def save(self):
        """Save data to disk."""
        dataIO.save_json(self.filepath, self.settings)

    def set_player(self, server, member, tag):
        """Associate player tag with Discord member.

        If tag already exists for member, overwrites it.
        """
        self.check_server(server)
        tag = SCTag(tag).tag
        if "players" not in self.settings["servers"][server.id]:
            self.settings["servers"][server.id]["players"] = {}
        players = self.settings["servers"][server.id]["players"]
        players[member.id] = tag
        self.settings["servers"][server.id]["players"] = players
        self.save()

    def tag2member(self, server, tag):
        """Return Discord member from player tag."""
        try:
            players = self.settings["servers"][server.id]["players"]
            for member_id, player_tag in players.items():
                if player_tag == tag:
                    return server.get_member(member_id)
        except KeyError:
            pass
        return None

    def server_settings(self, server):
        """Return server settings."""
        return self.settings["servers"][server.id]

    async def player_data(self, tag):
        """Return CRPlayerModel by tag."""
        tag = SCTag(tag).tag
        url = "{}{}".format(self.settings["profile_api_url"], tag)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=API_FETCH_TIMEOUT) as resp:
                    data = await resp.json()
        except json.decoder.JSONDecodeError:
            raise
        except asyncio.TimeoutError:
            raise

        file_path = self.cached_filepath(tag)
        dataIO.save_json(file_path, data)

        return CRPlayerModel(**data)

    def cached_player_data(self, tag):
        """Return cached data by tag."""
        file_path = self.cached_filepath(tag)
        if not os.path.exists(file_path):
            return None
        data = dataIO.load_json(file_path)
        return CRPlayerModel(is_cache=True, **data)

    def cached_player_data_timestamp(self, tag):
        """Return timestamp in days-since format of cached data."""
        file_path = self.cached_filepath(tag)
        timestamp = dt.datetime.fromtimestamp(os.path.getmtime(file_path))

        passed = dt.datetime.now() - timestamp

        days = passed.days
        hours, remainder = divmod(passed.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        p = inflect.engine()

        days_str = '{} {} '.format(days, p.plural("day", days)) if days > 0 else ''
        passed_str = (
            '{days} {hours} {hr} {minutes} {mn} {seconds} {sec} ago'
        ).format(
            days=days_str,
            hours=hours,
            hr=p.plural("hour", hours),
            minutes=minutes,
            mn=p.plural("minute", minutes),
            seconds=seconds,
            sec=p.plural("second", seconds)
        )

        return passed_str

    @staticmethod
    def cached_filepath(tag):
        """Cached clan data file path"""
        return os.path.join(PATH_PLAYERS, '{}.json'.format(tag))

    def member2tag(self, server, member):
        """Return player tag from member."""
        try:
            players = self.settings["servers"][server.id]["players"]
            for member_id, player_tag in players.items():
                if member_id == member.id:
                    return player_tag
        except KeyError:
            pass
        return None

    def trophy2arena(self, trophy):
        """Convert trophy to league based on Arenas."""
        result = None
        for arena in self.arenas:
            if trophy >= arena.TrophyLimit:
                result = arena
                break

        if result is not None:
            return '{}: {}'.format(result.TIDText, result.SubtitleTIDText)

        return ''

    def emoji(self, name=None, key=None):
        """Chest emojis by api key name or key.
        
        name is used by this cog.
        key is values returned by the api.
        Use key only if name is not set
        """
        emojis = {
            'Silver': 'chestsilver',
            'Gold': 'chestgold',
            'Giant': 'chestgiant',
            'Magic': 'chestmagical',
            'super_magical': 'chestsupermagical',
            'legendary': 'chestlegendary',
            'epic': 'chestepic'
        }
        if name is None:
            if key in emojis:
                name = emojis[key]
        for server in self.bot.servers:
            for emoji in server.emojis:
                if emoji.name == name:
                    return '<:{}:{}>'.format(emoji.name, emoji.id)
        return ''

    @property
    def profile_api_url(self):
        """Clan API URL."""
        return self.settings["profile_api_url"]

    @profile_api_url.setter
    def profile_api_url(self, value):
        """Set Clan API URL."""
        self.settings["profile_api_url"] = value
        self.save()

    @property
    def badge_url(self):
        """Clan Badge URL."""
        return self.settings["badge_url"]

    @badge_url.setter
    def badge_url(self, value):
        """lan Badge URL"""
        self.settings["badge_url"] = value
        self.save()

    def set_resources(self, server, value):
        """Show gold/gems or not."""
        self.settings[server.id]["show_resources"] = value

    def show_resources(self, server):
        """Show gold/gems or not."""
        try:
            return self.settings[server.id]["show_resources"]
        except KeyError:
            return False

# noinspection PyUnusedLocal
class CRProfile:
    """Clash Royale player profile."""

    def __init__(self, bot):
        """Init."""
        self.bot = bot
        self.model = Settings(bot, JSON)

    @commands.group(pass_context=True, no_pm=True)
    @checks.serverowner_or_permissions()
    async def crprofileset(self, ctx):
        """Clash Royale clan management API.

        Requires: Clash Royale API access by Selfish.
        """
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @crprofileset.command(name="initserver", pass_context=True)
    async def crprofileset_initserver(self, ctx):
        """Init CR Clan: server settings."""
        server = ctx.message.server
        self.model.init_server(server)
        await self.bot.say("Server settings initialized.")

    @crprofileset.command(name="initplayers", pass_context=True)
    async def crprofileset_initplayers(self, ctx):
        """Init CR Clan: players settings."""
        server = ctx.message.server
        self.model.init_players(server)
        await self.bot.say("Clan settings initialized.")

    @crprofileset.command(name="profileapi", pass_context=True)
    async def crprofileset_profileapi(self, ctx, url):
        """CR Clan API URL base.

        Format:
        If path is http://domain.com/path/LQQ
        Enter http://domain.com/path/
        """
        self.model.profile_api_url = url
        await self.bot.say("Profile API URL updated.")

    @crprofileset.command(name="badgeurl", pass_context=True)
    async def crprofileset_badgeurl(self, ctx, url):
        """badge URL base.

        Format:
        If path is hhttp://domain.com/path/LQQ
        Enter http://domain.com/path/
        """
        self.model.badge_url = url
        await self.bot.say("Badge URL updated.")

    @crprofileset.command(name="resources", pass_context=True)
    async def crprofileset_resources(self, ctx, enable:bool):
        """Show gold/gems in profile."""
        self.model.set_resources(ctx.message.server, enable)
        await self.bot.say(
            "CR profiles {} show resources.".format('will' if enable else 'will not')
        )

    @commands.group(pass_context=True, no_pm=True)
    async def crprofile(self, ctx):
        """Clash Royale Player Profile."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @crprofile.command(name="settag", pass_context=True, no_pm=True)
    async def crprofile_settag(
            self, ctx, playertag, member: discord.Member = None):
        """Set playertag to discord member.

        Setting tag for yourself:
        !crprofile settag C0G20PR2

        Setting tag for others (requires Bot Commander role):
        !crprofile settag C0G20PR2 SML
        !crprofile settag C0G20PR2 @SML
        !crprofile settag C0G20PR2 @SML#6443
        """
        server = ctx.message.server
        author = ctx.message.author

        sctag = SCTag(playertag)
        if not sctag.valid:
            await self.bot.say(sctag.invalid_error_msg)
            return

        allowed = False
        if member is None:
            allowed = True
        else:
            botcommander_roles = [
                discord.utils.get(
                    server.roles, name=r) for r in BOTCOMMANDER_ROLES]
            botcommander_roles = set(botcommander_roles)
            author_roles = set(author.roles)
            if len(author_roles.intersection(botcommander_roles)):
                allowed = True

        if not allowed:
            await self.bot.say("Only Bot Commanders can set tags for others.")
            return

        if member is None:
            member = ctx.message.author

        self.model.set_player(server, member, sctag.tag)

        await self.bot.say(
            "Associated player tag #{} with Discord Member {}.".format(
                sctag.tag, member.display_name
            ))

    @crprofile.command(name="gettag", pass_context=True, no_pm=True)
    async def crprofile_gettag(self, ctx, member: discord.Member = None):
        """Get playertag from Discord member."""
        server = ctx.message.server
        author = ctx.message.author
        if member is None:
            member = author
        tag = self.model.member2tag(server, member)
        if tag is None:
            await self.bot.say("Cannot find associated player tag.")
            return
        await self.bot.say(
            "Player tag for {} is #{}".format(
                member.display_name, tag))

    @crprofile.command(name="tag", pass_context=True, no_pm=True)
    async def crprofile_tag(self, ctx, tag):
        """Player profile by tag

        Display player info
        """
        await self.bot.type()
        sctag = SCTag(tag)

        if not sctag.valid:
            await self.bot.say(sctag.invalid_error_msg)
            return

        await self.display_profile(ctx, tag)

    @crprofile.command(name="get", pass_context=True, no_pm=True)
    async def crprofile_get(self, ctx, member: discord.Member = None):
        """Player profile

        if member is not entered, retrieve own profile
        """
        await self.bot.type()
        author = ctx.message.author
        server = ctx.message.server
        resources = False

        if member is None:
            member = author
            if self.model.show_resources(server):
                resources = True

        tag = self.model.member2tag(server, member)

        if tag is None:
            await self.bot.say(
                "{} has not set his player tag with the bot yet.".format(member.display_name)
            )
            return
        await self.display_profile(ctx, tag, resources=resources)

    async def display_profile(self, ctx, tag, resources=False):
        """Display profile."""
        sctag = SCTag(tag)
        if not sctag.valid:
            await self.bot.say(sctag.invalid_error_msg)
            return

        try:
            player_data = await self.model.player_data(sctag.tag)
        except json.decoder.JSONDecodeError:
            player_data = self.model.cached_player_data(tag)
        except asyncio.TimeoutError:
            player_data = self.model.cached_player_data(tag)

        if player_data is None:
            await self.bot.say("Unable to load from API.")
            return
        if player_data.is_cache:
            await self.bot.send_message(
                ctx.message.channel,
                (
                    "Unable to load from API. "
                    "Showing cached data from: {}.".format(
                        self.model.cached_player_data_timestamp(tag))
                )
            )

        server = ctx.message.server
        for em in self.embeds_profile(player_data, server=server, resources=resources):
            await self.bot.send_message(ctx.message.channel, embed=em)

    def embeds_profile(self, player: CRPlayerModel, server=None, resources=False):
        """Return Discord Embed of player profile."""
        embeds = []
        color = random_discord_color()

        # emoji_xp = self.model.emoji(name="experience")
        member = self.model.tag2member(server, player.tag)
        mention = ''
        if member is not None:
            mention = member.mention

        # header
        title = player.username
        description = '#{} {}'.format(player.tag, mention)
        em = discord.Embed(title=title, description=description, color=color)

        # clan
        em.set_thumbnail(url=player.clan_badge_url)
        header = {
            player.clan_name: player.clan_role,
            'Clan Tag': player.clan_tag,
            'Level': player.level,
            'Experience': player.xp
        }
        for k, v in header.items():
            em.add_field(name=k, value=v)
        embeds.append(em)

        # trophies
        em = discord.Embed(title=" ", color=color)

        def fmt(num, emoji_name):
            emoji = self.model.emoji(name=emoji_name)
            return '{:,} {}'.format(num, emoji)

        stats = {
            'Trophies': fmt(player.trophy_current, 'trophy'),
            'Highest Trophies': fmt(player.trophy_highest, 'trophy'),
            'Cards Found': fmt(player.cards_found, 'cards'),
            'Wins': fmt(player.wins, 'battle'),
            'Draws': fmt(player.draws, 'battle'),
            'Losses': fmt(player.losses, 'battle'),
            'Win Ratio': player.win_ratio,
            'Three-Crown Wins': fmt(player.three_crown_wins, 'crownblue'),
            player.arena_text: '{} {}'.format(
                player.arena_subtitle,
                player.arena_emoji(self.bot))
        }
        for k, v in stats.items():
            em.add_field(name=k, value=v)

        # chests
        # special chests
        key_list = ['super_magical', 'legendary', 'epic']
        chests = [(k, v) for k, v in player.chests.items() if k in key_list]
        # giant magical
        chests.append(('Giant', player.chest_giant_index))
        chests.append(('Magic', player.chest_magical_index))
        chests = sorted(chests, key=lambda c: c[1])

        cycle = [self.model.emoji(key=chest) for chest in player.chests["cycle"]]
        chest_str = ''.join(cycle)
        chest_out = ['{}{}'.format(self.model.emoji(key=c[0]), c[1]) for c in chests]
        chest_str = '{} . {}'.format(''.join(cycle), ' . '.join(chest_out))

        em.add_field(name="Chests", value=chest_str, inline=False)
        embeds.append(em)
        return embeds

    @crprofile.command(name="trophy2arena", pass_context=True, no_pm=True)
    async def crprofile_trophy2arena(self, ctx, trophy: int):
        """Convert trophies to arenas."""
        text = self.model.trophy2arena(trophy)
        await self.bot.say(text)



def check_folder():
    """Check folder."""
    if not os.path.exists(PATH):
        os.makedirs(PATH)
    if not os.path.exists(PATH_PLAYERS):
        os.makedirs(PATH_PLAYERS)


def check_file():
    """Check files."""
    if not dataIO.is_valid_json(JSON):
        dataIO.save_json(JSON, {})


def setup(bot):
    """Setup bot."""
    check_folder()
    check_file()
    n = CRProfile(bot)
    bot.add_cog(n)
