# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Extractors for https://lofter.com/"""

import itertools
from urllib import parse
import re

from .common import Extractor, Message
from .. import text, exception


BASE_PATTERN = (r"(?:https?://)?(.*)\.(?:lofter)\.com/")


class LofterExtractor(Extractor):
    """Base class for lofter extractors"""
    category = "lofter"
    directory_fmt = ("{category}", "{user[name]}")
    filename_fmt = "{id}_{num}.{extension}"
    archive_fmt = "{user[name]}_{id}_{num}"
    cookiedomain = ".lofter.com"

    def __init__(self, match):
        Extractor.__init__(self, match)
        self.username = match.group(1)
        self.root = f"https://{self.username}.lofter.com"

    def items(self):
        posts = self.posts()
        metadata = self.metadata()

        for post in posts:
            data = {}
            data.update(metadata)

            num = 0
            yield Message.Directory, data
            #for i in range(len(post['imgurls'])):
            for num, img in enumerate(post['imgurls']):
                img_metadata = text.nameext_from_url(img, data)
                img_metadata.update({'num': num})
                yield Message.Url, img, img_metadata

    def posts(self):
        """Return an iterable containing all relevant 'posts' objects"""

    def metadata(self):
        """Collect metadata for extractor job"""
        return {}


class LofterPostExtractor(LofterExtractor):
    """Base class for lofter post extractors"""
    subcategory = "post"
    pattern = BASE_PATTERN + r"post/([^/?#]+_[^/?#]+)"

    def __init__(self, match):
        LofterExtractor.__init__(self, match)
        self.permalink = match.group(2)
        self.post_metadata = {}

    def posts(self):
        url = f"{self.root}/post/{self.permalink}"
        post_html = self.request(url).text

        imgurls = re.findall(r'bigimgsrc="(.*?)\.*\?', post_html)
        tags_quote = re.findall(f'href="https://{self.username}' +
                                r'.lofter.com/tag/(.*?)"', post_html)
        tags = []
        for tag in tags_quote:
            tags.append(parse.unquote(tag))

        self.post_metadata = {
            "tags": tags, "id": self.permalink,
            "user": {
                "nick_name": re.findall(r'<h1><a href="/">(.*?)</a></h1>', post_html)[0],
                "name": self.username,
            },
            "img_count": len(imgurls),
            "title": re.findall(r"<title>(.*?)\-.*</title>", post_html)[0],
        }
        return ({"imgurls": imgurls},)

    def metadata(self):
        return self.post_metadata
