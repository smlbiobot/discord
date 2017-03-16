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
from discord.ext.commands import Context

try:
    from textblob import TextBlob
except ImportError:
    raise ImportError("Please install the textblob package from pip") from None

class NLP:
    """Natural Launguage Processing.
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def translate(self, ctx: Context, text: str, to_lang: str):
        """Translate to another language.

        Example:
        !translate "Simple is better than complex." es
        """
        blob = TextBlob(text)
        out = blob.translate(to=to_lang)
        await self.bot.say(out)

    @commands.command(pass_context=True)
    async def sentiment(self, ctx: Context, *, text: str):
        """Return sentiment analysis of a text."""
        blob = TextBlob(text)
        stmt = blob.sentiment
        await self.bot.say(
            "Polairty: {0.polarity}\n"
            "Subjectivity: {0.subjectivity}"
            "".format(stmt))

    @commands.command(pass_context=True)
    async def spellcheck(self, ctx: Context, *, text: str):
        """Auto-correct spelling mistakes."""
        b = TextBlob(text)
        await self.bot.say(b.correct())


def setup(bot):
    n = NLP(bot)
    bot.add_cog(n)