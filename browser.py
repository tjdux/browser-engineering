import socket
import ssl
import tkinter
import tkinter.font

class URL:
  # URL 파싱
  def __init__(self, url):
    self.scheme, url = url.split("://", 1)

    assert self.scheme in ["http", "https"] 
    
    if "/" not in url:
      url += "/"
    self.host, url = url.split('/', 1)
    self.path = "/" + url

    if self.scheme == "http":
      self.port = 80; # http의 port: 80
    elif self.scheme == "https":
      self.port = 443 # https는 일반적으로 443번 포트 사용

    # 사용자 지정 포트 (url에 포트가 있다면)
    if ":" in self.host:
      self.host, port = self.host.split(":", 1)
      self.port = int(port)
    

  def request(self):
    # 서버에 연결
    s = socket.socket(
      family=socket.AF_INET,
      type=socket.SOCK_STREAM,
      proto=socket.IPPROTO_TCP
    )
    # https일 시 ssl 라이브러리 사용
    if self.scheme == "https":
      ctx = ssl.create_default_context()
      s = ctx.wrap_socket(s, server_hostname=self.host)
    s.connect((self.host, self.port))

    # 요청 메시지 전송
    request = f"GET {self.path} HTTP/1.1\r\n"
    request += f"Host: {self.host}\r\n"
    request += "\r\n"
    s.send(request.encode("utf8"))

    # 응답 메시지 읽기 
    response = s.makefile("r", encoding="utf-8", newline="\r\n")
    statusline = response.readline()
    version, status, explanation = statusline.split(" ", 2)
    response_headers = {}
    while True:
      line = response.readline()
      if line == "\r\n": break
      header, value = line.split(":", 1)
      response_headers[header.casefold()] = value.strip()
    assert "transfer-encoding" not in response_headers
    assert "content-encoding" not in response_headers
    body = response.read()
    s.close()

    return body;

class Text:
  def __init__(self, text, parent):
    self.text = text
    self.children = [] # 텍스트 노드에는 필요 없지만 일관성을 위해!
    self.parent = parent

  def __repr__(self):
    return repr(self.text)

class Element:
  def __init__(self, tag, attributes, parent):
    self.tag = tag
    self.attributes = attributes
    self.children = [] 
    self.parent = parent

  def __repr__(self):
    return f"<{self.tag}>"

def print_tree(node, indent=0):
  print(" " * indent, node)
  for child in node.children:
    print_tree(child, indent + 2)

class HTMLParser:
  # 분석 중인 소스 코드와 불완전 트리 저장
  def __init__(self, body):
    self.body = body
    self.unfinished = [] # 첫 번째 노드: HTML 트리의 루트, 마지막 노드: 가장 최근 추가된 미완성 태그
  
  def parse(self):
    text = ""
    in_tag = False
    for c in self.body:
      if c == "<":
        in_tag = True
        if text: self.add_text(text)
        text = ""
      elif c == ">":
        in_tag = False
        self.add_tag(text)
        text = ""
      else:
        text += c
    if not in_tag and text:
      self.add_text(text)
    return self.finish()
  
  # 트리에 텍스트 노드 추가
  def add_text(self, text):
    if text.isspace(): return # 화이트스페이스만 있는 텍스트노드 건너뛰기
    self.implicit_tags(None)
    parent = self.unfinished[-1]
    node = Text(text, parent)
    parent.children.append(node)

  SELF_CLOSING_TAGS = [
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr"
  ]

  # 어트리뷰트 처리
  def get_attributes(self, text):
    parts = text.split()
    tag = parts[0].casefold()
    attributes = {}
    for attrpair in parts[1:]:
      if "=" in attrpair:
        key, value = attrpair.split("=", 1)
        if len(value) > 2 and value[0] in ["'", "\""]:
          value = value[1:-1]
        attributes[key.casefold()] = value
      else:
        attributes[attrpair.casefold()] = ""
    return tag, attributes

  # 트리에 태그 노드 추가
  def add_tag(self, tag):
    tag, attributes = self.get_attributes(tag)
    if tag.startswith("!"): return # doctype, 주석 버리기
    self.implicit_tags(tag)
    if tag.startswith("/"):
      if len(self.unfinished) == 1: return
      node = self.unfinished.pop()
      parent = self.unfinished[-1]
      parent.children.append(node)
    elif tag in self.SELF_CLOSING_TAGS:
      parent = self.unfinished[-1]
      node = Element(tag, attributes, parent)
      parent.children.append(node)
    else: 
      parent = self.unfinished[-1] if self.unfinished else None
      node = Element(tag, attributes, parent)
      self.unfinished.append(node)

  # <head>안에 놓여야 하는 태그들
  HEAD_TAGS = [
    "base", "basefont", "bgsound", "noscript",
    "link", "meta", "title", "style", "script"
  ]

  # 암시적 태그
  def implicit_tags(self, tag):
    while True:
      open_tags = [node.tag for node in self.unfinished]
      if open_tags == [] and tag != "html":
        self.add_tag("html")
      elif open_tags == ["html"] and tag not in ["head", "body", "/html"]:
        if tag in self.HEAD_TAGS:
          self.add_tag("head")
        else:
          self.add_tag("body")
      elif open_tags == ["html", "head"] and tag not in ["/head"] + self.HEAD_TAGS:
        self.add_tag("/head")
      else:
        break;
    
  # 파싱을 끝내면 미완성 노드를 모두 정리하여 불완전 트리를 완전 트리로
  def finish(self):
    if not self.unfinished:
      self.implicit_tags(None)
    while len(self.unfinished) > 1:
      node = self.unfinished.pop()
      parent = self.unfinished[-1]
      parent.children.append(node)
    return self.unfinished.pop()

WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18

SCROLL_STEP = 100

FONTS = {}

def get_font(size, weight, style):
  key = (size, weight, style)
  if key not in FONTS:
    font = tkinter.font.Font(size=size, weight=weight, slant=style)
    label = tkinter.Label(font=font)
    FONTS[key] = (font, label)
  return FONTS[key][0]

# 레이아웃 트리의 루트 역할 
class DocumentLayout:
  def __init__(self, node):
    self.node = node
    self.parent = None
    self.children = []

    # 크기, 위치
    self.x = None
    self.y = None
    self.width = None
    self.height = None

  def layout(self):
    child = BlockLayout(self.node, self, None)
    self.children.append(child)

    self.width = WIDTH - 2*HSTEP
    self.x = HSTEP
    self.y = VSTEP

    child.layout() # 트리 구축을 위해 재귀적 호출 
    self.height = child.height

  def paint(self):
    return []

BLOCK_ELEMENTS = [
  "html", "body", "article", "section", "nav", "aside",
  "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
  "footer", "address", "p", "hr", "pre", "blockquote",
  "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
  "figcaption", "main", "div", "table", "form", "fieldset",
  "legend", "details", "summary"
]

def paint_tree(layout_object, display_list):
  display_list.extend(layout_object.paint())

  for child in layout_object.children:
    paint_tree(child, display_list)


class BlockLayout:
  def __init__(self, node, parent, previous):
    # 트리로 만들기 위해 자식 포인터, 부모 포인터, 이전 형제에 대한 포인터 추가
    self.node = node 
    self.parent = parent
    self.previous = previous
    self.children = []
    self.display_list = []

    # 크기, 위치
    self.x = None
    self.y = None
    self.width = None
    self.height = None

  def layout(self):
    # 객체는 부모의 왼쪽 가장자리에서 시작하여 부모 엘리먼트를 채워감
    if self.previous:
      self.y = self.previous.y + self.previous.height
    else:
      self.y = self.parent.y
    self.x = self.parent.x
    self.width = self.parent.width

    mode = self.layout_mode()
    if mode == "block":
      self.height = sum([
        child.height for child in self.children
      ])
      previous = None
      for child in self.node.children:
        next = BlockLayout(child, self, previous)
        self.children.append(next)
        previous = next
    else: 
      self.display_list = []

      self.cursor_x = 0
      self.cursor_y = 0
      self.weight = "normal"
      self.style = "roman"
      self.size = 12
      self.height = self.cursor_y

      self.line = []
      self.recurse(self.node)
      self.flush()

    for child in self.children:
      child.layout()

  def word(self, word):
    font = get_font(self.size, self.weight, self.style)
    w = font.measure(word)
    # 첫 번째 패스: 줄에 어떤 단어가 들어가는지 식별, x 위치 계산 
    if self.cursor_x + w > self.width:
      self.flush()
    self.line.append(((self.cursor_x, word, font)))
    self.cursor_x += w + font.measure(" ")

  # 텍스트 관련 태그인지 블록 태그인지 구분 
  def layout_mode(self):
    if isinstance(self.node, Text):
      return "inline"
    elif any([isinstance(child, Element) and \
              child.tag in BLOCK_ELEMENTS
              for child in self.node.children]):
      return "block"
    elif self.node.children:
      return "inline"
    else:
      return "block"

  def recurse(self, tree):
    if isinstance(tree, Text):
      for word in tree.text.split():
        self.word(word)
    else:
      self.open_tag(tree.tag)
      for child in tree.children:
        self.recurse(child)
      self.close_tag(tree.tag)

  def layout_intermediate(self):
    # node, child가 가리키는 HTML 트리와 self, previous, next가 가리키는 레이아웃 트리
    # HTML 트리로 레이아웃 트리를 구축
    previous = None
    for child in self.node.children:
      next = BlockLayout(child, self, previous)
      self.children.append(next)
      previous = next 

  def flush(self):
    # 기준선을 따라 단어들을 정렬
    if not self.line: return
    metrics = [font.metrics() for _, _, font in self.line]
    max_ascent = max([metric["ascent"] for metric in metrics]) # 높이가 가장 높은 글자
    baseline = self.cursor_y + 1.25 * max_ascent # 💡 더하는 이유: y좌표는 아래 방향으로 증가!
    # 디스플레이 리스트에 모든 단어들을 추가
    for rel_x, word, font in self.line:
      x = self.x + rel_x
      y = self.y + baseline - font.metrics("ascent")
      self.display_list.append((x, y, word, font))
    max_descent = max([metric["descent"] for metric in metrics])
    # cursor_x와 cursor_y 필드를 업데이트 
    self.cursor_y = baseline + 1.25 * max_descent
    self.cursor_x = 0
    self.line = []

  def open_tag(self, tag):
    if tag == "i":
      self.style = "italic"
    elif tag == "b":
      self.weight = "bold"
    elif tag == "small":
      self.size -= 2
    elif tag == "big":
      self.size += 4
    elif tag == "br":
      self.flush()
    
  def close_tag(self, tag):
    if tag == "i":
      self.style = "roman"
    elif tag == "b":
      self.weight = "normal"
    elif tag == "small":
      self.size += 2
    elif tag == "big":
      self.size -= 4
    elif tag == "p":
      self.flush()
      self.cursor_y += VSTEP

  def paint(self):
    return self.display_list

class Browser:
  def __init__(self):
    self.window = tkinter.Tk()
    self.canvas = tkinter.Canvas(
      self.window,
      width=WIDTH,
      height=HEIGHT
    )
    self.scroll = 0 # 스크롤한 거리
    self.window.bind("<Down>", self.scrolldown) # bind
    self.canvas.pack()

    self.display_list = []

  # 저장된 위치를 기반으로 각 문자를 그림 - 화면 좌표만 고려
  def draw(self):
    self.canvas.delete("all")
    for x, y, word, font in self.display_list:
      if y > self.scroll + HEIGHT: continue # 창의 아래문자 건너뛰기
      if y + VSTEP < self.scroll: continue # 창의 위의 문자 건너뛰기
      self.canvas.create_text(x, y-self.scroll, text=word, font=font, anchor="nw")

  # 웹페이지 로드
  def load(self, url):
    body = url.request()
    self.nodes = HTMLParser(body).parse()
    self.documnet = DocumentLayout(self.nodes) # 레이아웃 객체 생성
    self.documnet.layout() # 레이아웃 수행 
    paint_tree(self.documnet, self.display_list)
    self.draw()

  # 스크롤 
  def scrolldown(self, e):
    self.scroll += SCROLL_STEP
    self.draw()

# load 함수 실행
if __name__ == "__main__":
  import sys
  Browser().load(URL(sys.argv[1])) # sys.argv: 파이썬 스크립트 실행 시 전달되는 인자들의 리스트
  tkinter.mainloop()