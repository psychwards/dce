import os, re
import binascii
import hashlib
import urllib
import pathlib
import json
import filetype
from datetime import datetime, timedelta
import emoji
import httpx
import strings
import time
from rich import print
from threading import Thread


class export:
    def __init__(self, data) -> None:
        self.session = httpx.Client()
        self.data = data
        self.message_types = {
            0: "Default",
            1: "RecipinetAdd",
            2: "RecipinetRemove",
            3: "Call",
            4: "ChannelNameChange",
            5: "ChannelIconChange",
            6: "ChannelPinnedMessage",
            19: "Reply",
        }
        self.sticker_formats = {
            1: "png",  # Picture
            2: "png",  # Animated Picture (Supposed to be .apng but oh well thats discord)
            3: "json",  # Lottio Format
            4: "gif",  # Graphics Interchange Format
        }
        self.folder = os.path.join(
            pathlib.Path(__file__).parent.resolve(), str(int(time.time()))
        )

    def get_avatar(self, path, user) -> str:
        fileext = "gif" if user["avatar"].startswith("a_") else "png"
        filename = os.path.join(
            path,
            f"{user['avatar']}_{binascii.crc32(bytes(user['avatar'], 'utf-8'))}.{fileext}",
        )
        if not os.path.exists(filename):
            with open(
                filename,
                "wb",
            ) as f:
                f.write(
                    self.session.get(
                        url=f"{strings.CDN}/avatars/{user['id']}/{user['avatar']}.{fileext}",
                        params={"size": "4096"},
                    ).content
                )
        return filename

    def get_messages(self, channel, account, folder=os.PathLike or str, after=None):
        if after is None:
            after = 0
        jsn = []
        # sourcery skip: low-code-quality
        while True:
            messages = self.session.get(
                f"{strings.BASE}/channels/{channel['id']}/messages",
                params={"after": after, "limit": "100"},
                headers={"Authorization": account["token"]},
            ).json()
            if messages == []:
                print(
                    f"[[bold pink1]i[/bold pink1]] [bold medium_purple1]no messages found in [bold pink1]{channel['id']}[/bold pink1] | after: [bold pink1]{after}[/bold pink1], skipping[/bold medium_purple1]"
                )
                if after == "0":
                    return []
                break
            for message in reversed(messages):
                
                base = {
                    "id": message["id"],
                    "type": self.message_types[message["type"]],
                    "timestamp": message["timestamp"],
                    "timestampEdited": message["edited_timestamp"],
                    "isPinned": message["pinned"],
                    "content": message["content"],
                    "author": {
                        "id": message["author"]["id"],
                        "name": message["author"]["username"],
                        "discriminator": message["author"]["discriminator"],
                        "nickname": message["author"]["global_name"]
                        or message["author"]["username"],
                        "avatarUrl": self.get_avatar(
                            path=folder, user=message["author"]
                        )
                        if message["author"]["avatar"]
                        else self.download_asset(
                            asset=strings.DEFAULT_ICON_OR_MISSING,
                            folder=folder,
                        ),
                    },
                    "attachments": [
                        {
                            "id": attachment["id"],
                            "url": self.download_asset(
                                asset=attachment["url"],
                                folder=folder,
                                type=attachment["proxy_url"].split(".")[-1],
                            ),
                            "fileName": attachment["filename"],
                            "fileSizeBytes": attachment["size"],
                        }
                        for attachment in message["attachments"]
                    ],
                    "embeds": self.embeds(embeds=message["embeds"], folder=folder),
                    "stickers": [
                        {
                            "id": sticker["id"],
                            "name": sticker["name"],
                            "format": self.sticker_formats[sticker["format_type"]],
                            "sourceUrl": self.download_asset(
                                asset=f"{strings.CDN}/stickers/{sticker['id']}.{self.sticker_formats[sticker['format_type']]}",
                                folder=folder,
                                type=self.sticker_formats[sticker["format_type"]],
                            ),
                        }
                        for sticker in message["sticker_items"]
                    ]
                    if "sticker_items" in message
                    else [],
                    "reactions": [
                        {
                            "emoji": {
                                "id": reaction["emoji"]["id"],
                                "name": reaction["emoji"]["name"]
                                or f"<{'a:' if reaction['emoji'].get('animated', False) else ''}{reaction['emoji']['name']}:{reaction['emoji']['id']}>",
                                "code": emoji.demojize(reaction["emoji"]["name"]).strip(
                                    ":"
                                )
                                if reaction["emoji"]["id"] is None
                                else reaction["emoji"]["name"],
                                "isAnimated": reaction["emoji"].get("animated", False),
                                "imageUrl": self.download_asset(
                                    asset=f"{strings.CDN}/emojis/{reaction['emoji']['id']}.{'gif' if reaction['emoji'].get('animated', False) else 'png'}"
                                    if reaction["emoji"]["id"] is not None
                                    else f"{strings.TWTEMOJI}/{'-'.join([hex(ord(emojichar))[2:] for emojichar in reaction['emoji']['name']])}.svg",
                                    folder=folder,
                                    type=f"{'gif' if reaction['emoji'].get('animated', False) else 'png'}"
                                    if reaction["emoji"]["id"] is not None
                                    else "svg",
                                ),
                            },
                            "count": reaction["count"],
                            "users": [
                                {
                                    "id": user["id"],
                                    "name": user["username"],
                                    "discriminator": user["discriminator"],
                                    "nickname": user["global_name"] or user["username"],
                                    "avatarUrl": self.get_avatar(
                                        path=folder, user=message["author"]
                                    )
                                    if message["author"]["avatar"]
                                    else self.download_asset(
                                        asset=strings.DEFAULT_ICON_OR_MISSING,
                                        folder=folder,
                                    ),
                                }
                                for user in (
                                    self.session.get(
                                        url=f"{strings.BASE}/channels/{channel['id']}/messages/{message['id']}/reactions/{urllib.parse.quote(reaction['emoji']['name'].strip(':') if reaction['emoji']['id'] is None else reaction['emoji']['name'] + ':' + reaction['emoji']['id'])}",
                                        headers={"Authorization": account["token"]},
                                    ).json()
                                )
                            ],
                        }
                        for reaction in message["reactions"]
                    ]
                    if "reactions" in message
                    else [],
                    "mentions": [
                        {
                            "id": user["id"],
                            "name": user["username"],
                            "discriminator": user["discriminator"],
                            "nickname": user["global_name"] or user["username"],
                            "avatarUrl": self.get_avatar(
                                path=folder, user=message["author"]
                            )
                            if message["author"]["avatar"]
                            else self.download_asset(
                                asset=strings.DEFAULT_ICON_OR_MISSING,
                                folder=folder,
                            ),
                        }
                        for user in message["mentions"]
                    ],
                }
                if "message_reference" in message:
                    base["reference"] = {
                        "messageId": message["message_reference"].get("message_id"),
                        "channelId": message["message_reference"].get("channel_id"),
                        "guildId": message["message_reference"].get("guild_id"),
                    }
                if message["type"] == 3:  # Call
                    base["callEndedTimestamp"] = message["call"]["ended_timestamp"]
                if message["type"] in [1, 2]:  # Call
                    base[
                        "content"
                    ] = f"{'Added' if message['type'] == 1 else 'Removed'} {base['mentions'][0]['nickname']} to the group."
                jsn.append(base)
                print(
                    f"[[bold pink1]+[/bold pink1]] [bold medium_purple1]logged [bold pink1]{channel['id']}[/bold pink1] -> [bold pink1]{message['id']}[/bold pink1][/bold medium_purple1]"
                )
                after = message["id"]
        return jsn

    def embeds(self, embeds, folder):
        for embed in embeds:
            if embed["type"] == "image":
                embed["url"] = self.download_asset(
                    asset=embed["thumbnail"]["url"],
                    folder=folder,
                    type=embed["thumbnail"]["url"].split(".")[-1]
                )
            elif embed["type"] == "video":
                if "proxy_url" in embed["video"]:
                    embed["video"]["url"] = self.download_asset(
                        asset=embed["video"]["proxy_url"],
                        folder=folder,
                        type=embed["video"]["proxy_url"].split(".")[-1],
                    )
                if "thumbnail" in embed:
                    embed["thumbnail"]["url"] = self.download_asset(
                        asset=embed["thumbnail"]["url"], folder=folder, type="jpeg"
                    )
        return embeds
    
    def clean_string(self, string):
        return "".join(x for x in string if x.isalnum())

    def download_asset(self, asset: str, folder: os.PathLike, type: str = None) -> str:
        try:
            request = self.session.get(
                url=asset,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
                },
            )
        except Exception as e:
            print(
                f"[[bold pink1]![/bold pink1]] [bold medium_purple1]couldn't download asset: [bold pink1]{asset}[/bold pink1][/bold medium_purple1] | {e}"
            )
            return asset
        else:
            if request.status_code != 200:
                print(
                    f"[[bold pink1]![/bold pink1]] [bold medium_purple1]couldn't download asset: [bold pink1]{asset}[/bold pink1][/bold medium_purple1] | {request.status_code}"
                )
                return asset
            filename = f"{hashlib.sha256(request.content).hexdigest()}.{self.clean_string(type or filetype.guess_extension(request.content) or 'unknown')}"
            
            with open(os.path.join(folder, filename), "wb") as f:
                f.write(request.content)
            return os.path.join(folder, filename)

    def job(self, account, channel):
        print(
            f"[[bold pink1]i[/bold pink1]] [bold medium_purple1]downloading/exporting assets/messages in [bold pink1]{channel['id']}[/bold pink1] | after: 0[/bold medium_purple1]"
        )
        folder = os.path.join(self.folder, f"{channel['file_name']}_assets")
        os.makedirs(name=folder)
        messages = self.get_messages(channel=channel, account=account, folder=folder)
        jsn = {
            "guild": {
                "id": "0",
                "name": "Private Messages",
                "iconUrl": "",
            },
            "channel": {
                "id": channel["id"],
                "type": "DirectGroupTextChat"
                if channel["type"] == 3
                else "DirectTextChat",
                "categoryId": None,
                "category": "Group" if channel["type"] == 3 else "Private",
                "name": channel["file_name"],
                "topic": None,
            },
            "messages": messages,
            "messageCount": len(messages),
        }
        if jsn["messages"] != []:
            with open(os.path.join(folder, "..", channel["file_name"]), "w") as f:
                jsn["guild"]["iconUrl"] = self.download_asset(
                    asset=strings.DEFAULT_ICON_OR_MISSING,
                    folder=folder,
                )
                f.write(json.dumps(jsn, indent=4))
                print(
                    f'[[bold pink1]+[/bold pink1]] [bold medium_purple1]done scraping [bold pink1]{channel["id"]}[/bold pink1][/bold medium_purple1]'
                )
        else:
            print(
                f'[[bold pink1]![/bold pink1]] [bold medium_purple1]didnt find any messages in [bold pink1]{channel["id"]}[/bold pink1], deleting files and assets folder generated...[/bold medium_purple1]'
            )

            os.rmdir(folder)

    def start(self):
        for account in self.data:
            for channel in account["channels"]:
                Thread(
                    target=self.job,
                    args=(
                        account,
                        channel,
                    ),
                ).start()
