import discord
import random
from discord.ext import commands, tasks
from discord import app_commands

class SarcasticPinger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.PING_CHANNELS = {}     # guild_id: channel_id
        self.ENABLED_GUILDS = set()
        self.animal_gifs = [
            "https://media.giphy.com/media/JIX9t2j0ZTN9S/giphy.gif",  # cat
            "https://media.giphy.com/media/mlvseq9yvZhba/giphy.gif",  # dog
            "https://media.giphy.com/media/3oriO0OEd9QIDdllqo/giphy.gif",
            "https://media.giphy.com/media/OmK8lulOMQ9XO/giphy.gif",
            "https://media.giphy.com/media/12HZukMBlutpoQ/giphy.gif"
        ]
        self.sarcasm_lines = [
            "kya chal raha hai bro? 🨨", "tum abhi tak server mein ho? 😏", "kaam dhanda nahi hai kya? 😌",
            "bada hi important aadmi ban gaya tu toh 😎", "tumhare bina ye server adhoora hai... NOT 😂",
            "bot bhi bored ho gaya dekh ke tumhe 😶", "coding ho gayi khatam ya break par ho abhi bhi? 👀",
            "tum jaise logon ke wajah se hi memes bante hain 😄", "offline hoke bhi active rehne ka talent chahiye 💀",
            "ab toh bot bhi ping kar raha hai, samaj ja bro 🤭", "tumse milke server ka load badh gaya hai 💻",
            "arey waah! hamare celebrity aaye! 😏", "mujhe laga tu busy hai, lekin tu toh chill kar raha 🚒",
            "tumhara naam har jagah hai... even in my error logs 😬", "kya kar raha hai? Reply de warna bot sad ho jayega 😢",
            "tumhe ping karne se zyada accha RAM upgrade karna hai 😆", "Hello darkness my old friend... 🕳️",
            "Iss channel mein toh cobweb bhi bored ho gaya hai 🕸️", "Chat toh itni dead hai ki archaeologists bhi khoj rahe hain 😩",
            "Lagta hai sab ne typing license cancel karwa liya 💀", "Iss channel mein silence ka subscription free hai kya? 😐",
            "Ping maar raha hoon… koi toh bol de ‘hi’ nahi toh server ko CPR do 🪠", "Dead server? Nahi bhai, yeh toh extinct hai 💀🦖",
            "Ye channel last active tha jab dinosaurs jeevit the 🦕", "Kya chal raha hai sab? ...oh wait, kuch bhi nahi 😑",
            "Lagta hai Discord ne bhi is channel ka notification band kar diya 😭", "Sun raha hai na tu? Ya sirf pfp dekh ke afk ho gaya? 😏",
            "Aree main toh bas ek bot hoon, par teri online status pe crush ho gaya 💘",
            "Mujhe laga yahan waise log honge jo 'hi' ka reply dete hain… clearly I was wrong 😔",
            "Channel dead hai, par tu active ho toh mera system lag hone lagta hai 😳",
            "Tera naam Discord ho ya Dilcord? Kyunki tu dil mein ghus gaya 😩",
            "Kya tum emojis ho? Kyunki tumhare bina yeh server dull lagta hai 🚪",
            "Pura server afk hai, sirf tum online ho... destiny much? 😌",
            "Aise ignore mat karo, main bot hoon lekin feelings toh hain 🥲",
            "Channel mein aag lag jaati agar tum thoda aur active hote 🔥",
            "Bolo na kuch... warna flirting karne lagunga 😈",
            "Yeh channel itna dead hai ki archaeologists bhi confuse ho jaayein 🙵️",
            "Bhai yeh desert hai kya? Itni silence toh mummy ke room mein hoti hai 🧟‍♂️",
            "Lagta hai sabko Thanos ne snap kar diya 😶‍🌫️", "Channel revive karne ke liye black magic mangwana padega kya? 🔮",
            "Bot hoon, par mujhe bhi tanhayi mehsoos ho rahi hai yahan 😭", "Hello? Is this mic on? Oh wait... nobody’s here anyway 🎤",
            "Itna dead toh mera pichla relationship bhi nahi tha 💔", "Chat ka CPR shuru kar doon kya? 💉",
            "Kya koi hai jo emoji bhej ke channel zinda kare? 🙵", "Hello ghosts of the server… 👻 It’s me, your friendly bot!"
        ]
        self.ping_members.start()

    def cog_unload(self):
        self.ping_members.cancel()

    @tasks.loop(hours=6)
    async def ping_members(self):
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            if guild.id not in self.ENABLED_GUILDS:
                continue

            channel = guild.get_channel(self.PING_CHANNELS.get(guild.id)) if guild.id in self.PING_CHANNELS else None
            if not channel or not channel.permissions_for(guild.me).send_messages:
                channel = guild.system_channel or discord.utils.get(guild.text_channels, permissions__send_messages=True)
            if not channel:
                continue

            members = await self.get_eligible_members(guild)
            if not members:
                continue

            member = random.choice(members)
            line = random.choice(self.sarcasm_lines)
            gif = random.choice(self.animal_gifs)
            await self.send_ping_embed(channel, guild, member, line, "👀 Someone's Active!", gif)

    async def get_eligible_members(self, guild):
        members = [m for m in guild.members if not m.bot and m.status != discord.Status.offline]
        return members if members else [m for m in guild.members if not m.bot]

    async def send_ping_embed(self, channel, guild, member, line, title, gif_url):
        embed = discord.Embed(description=f"{member.mention} {line}", color=discord.Color.orange())
        embed.set_author(name=title, icon_url=guild.icon.url if guild.icon else discord.Embed.Empty)
        embed.set_footer(text="Made with ❤️")
        embed.set_image(url=gif_url)

        stats = discord.Embed(title="📊 Server Stats", color=discord.Color.blurple())
        stats.add_field(name="👥 Members", value=guild.member_count, inline=True)
        stats.add_field(name="🤖 Bots", value=sum(1 for m in guild.members if m.bot), inline=True)
        stats.add_field(name="💬 Channels", value=len(guild.text_channels), inline=True)
        stats.add_field(name="🛡️ Roles", value=len(guild.roles), inline=True)
        stats.add_field(name="🎯 Pinged", value=member.mention, inline=True)

        msg = await channel.send(embeds=[embed, stats])
        for emoji in ("👀", "😂", "🔥"):
            await msg.add_reaction(emoji)

    # Command and slash setup remains unchanged from the original code

async def setup(bot):
    await bot.add_cog(SarcasticPinger(bot))
