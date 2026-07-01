#!/usr/bin/env python3
"""Web search tool for Humitron."""
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from humitron.models.tools import ToolResult


class DDGParser(HTMLParser):
    """Simple HTML parser to extract DuckDuckGo search results."""
    def __init__(self):
        super().__init__()
        self.results = []
        self.in_result = False
        self.current = {}
        self.capture_text = False
        self.tag_stack = []
    
    def handle_starttag(self, tag, attrs):
        self.tag_stack.append(tag)
        attrs_dict = dict(attrs)
        
        if tag == "a" and attrs_dict.get("class") == "result__snippet":
            self.in_result = True
            self.current = {"url": attrs_dict.get("href", "")}
        elif tag == "a" and attrs_dict.get("class") == "result__url":
            self.capture_text = True
            self.current["title"] = ""
    
    def handle_endtag(self, tag):
        if self.tag_stack:
            self.tag_stack.pop()
        if tag == "a" and self.in_result:
            self.in_result = False
            if self.current.get("snippet"):
                self.results.append(self.current)
                self.current = {}
        elif tag == "a" and self.capture_text:
            self.capture_text = False
    
    def handle_data(self, data):
        if self.in_result and data.strip():
            self.current["snippet"] = data.strip()
        elif self.capture_text and data.strip():
            self.current["title"] = data.strip()


def web_search(query: str, max_results: int = 5) -> ToolResult:
    """
    Search the web using DuckDuckGo HTML (free, no API key).
    
    Args:
        query: Search query string.
        max_results: Maximum number of results to return.
        
    Returns:
        ToolResult with search results or error.
    """
    try:
        # Build search URL
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        # Make request with a browser-like user agent
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode("utf-8")
        
        # Parse results
        parser = DDGParser()
        parser.feed(html)
        
        if not parser.results:
            # Fallback: try to extract from page text
            return ToolResult(
                success=True,
                output=f"Search completed for '{query}'. No structured results found. Try a different query."
            )
        
        # Format results
        output_lines = [f"Search results for: {query}\n"]
        for i, result in enumerate(parser.results[:max_results], 1):
            title = result.get("title", "No title")
            snippet = result.get("snippet", "No snippet")
            url = result.get("url", "No URL")
            output_lines.append(f"{i}. {title}")
            output_lines.append(f"   {snippet}")
            output_lines.append(f"   URL: {url}\n")
        
        return ToolResult(success=True, output="\n".join(output_lines))
    
    except Exception as e:
        return ToolResult(success=False, output="", error=f"Web search failed: {str(e)}")