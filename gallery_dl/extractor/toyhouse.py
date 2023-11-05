# -*- coding: utf-8 -*-

# Copyright 2022-2023 Mike Fährmann
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Extractors for https://toyhou.se/"""

from .common import Extractor, Message
from .. import text, util

BASE_PATTERN = r"(?:https?://)?(?:www\.)?toyhou\.se"


class ToyhouseExtractor(Extractor):
    """Base class for toyhouse extractors"""
    category = "toyhouse"
    root = "https://toyhou.se"
    directory_fmt = ("{category}", "{user|artists!S}")
    archive_fmt = "{id}"

    def __init__(self, match):
        Extractor.__init__(self, match)
        self.user = match.group(1)
        self.offset = 0

    def items(self):
        metadata = self.metadata()

        for post in util.advance(self.posts(), self.offset):
            if metadata:
                post.update(metadata)
            text.nameext_from_url(post["url"], post)
            post["id"], _, post["hash"] = post["filename"].partition("_")
            yield Message.Directory, post
            yield Message.Url, post["url"], post

    def posts(self):
        return ()

    def metadata(self):
        return None

    def skip(self, num):
        self.offset += num
        return num

    def _parse_post(self, post, needle='<a href="'):
        extr = text.extract_from(post)
        return {
            "url": extr(needle, '"'),
            "date": text.parse_datetime(extr(
                'Credits\n</h2>\n<div class="mb-1">', '<'),
                "%d %b %Y, %I:%M:%S %p"),
            "artists": [
                text.remove_html(artist)
                for artist in extr(
                    '<div class="artist-credit">', '</div>\n</div>').split(
                    '<div class="artist-credit">')
            ],
            "characters": text.split_html(extr(
                '<div class="image-characters', '</div>\n</div>'))[2:],
        }

    def _pagination(self, path):
        url = self.root + path
        params = {"page": 1}

        while True:
            page = self.request(url, params=params).text

            cnt = 0
            for post in text.extract_iter(
                    page, '<li class="gallery-item">', '</li>'):
                cnt += 1
                yield self._parse_post(post)

            if cnt == 0 and params["page"] == 1:
                token, pos = text.extract(
                    page, '<input name="_token" type="hidden" value="', '"')
                if not token:
                    return
                data = {
                    "_token": token,
                    "user"  : text.extract(page, 'value="', '"', pos)[0],
                }
                self.request(self.root + "/~account/warnings/accept",
                             method="POST", data=data, allow_redirects=False)
                continue

            if cnt < 18:
                return
            params["page"] += 1


class ToyhouseArtExtractor(ToyhouseExtractor):
    """Extractor for artworks of a toyhouse user"""
    subcategory = "art"
    pattern = BASE_PATTERN + r"/([^/?#]+)/art"
    example = "https://www.toyhou.se/USER/art"

    def posts(self):
        return self._pagination("/{}/art".format(self.user))

    def metadata(self):
        return {"user": self.user}


class ToyhouseImageExtractor(ToyhouseExtractor):
    """Extractor for individual toyhouse images"""
    subcategory = "image"
    pattern = (r"(?:https?://)?(?:"
               r"(?:www\.)?toyhou\.se/~images|"
               r"f\d+\.toyhou\.se/file/[^/?#]+/(?:image|watermark)s"
               r")/(\d+)")
    example = "https://toyhou.se/~images/12345"

    def posts(self):
        url = "{}/~images/{}".format(self.root, self.user)
        return (self._parse_post(self.request(url).text, '<img src="'),)
