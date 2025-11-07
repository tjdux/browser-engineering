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
  def __init__(self, text):
    self.text = text
  
class Tag:
  def __init__(self, tag):
    self.tag = tag

# 태그, 텍스트 반환
def lex(body):
  out = []
  buffer = ""
  in_tag = False
  for c in body:
    if c == "<":
      in_tag = True
      if buffer: out.append(Text(buffer))
      buffer = ""
    elif c == ">":
      in_tag = False
      out.append(Tag(buffer))
      buffer = ""
    else:
      buffer += c
  if not in_tag and buffer:
    out.append(Text(buffer))
  return out


WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18

class Layout:
  def __init__(self, tokens):
    self.display_list = []    
    self.cursor_x = HSTEP
    self.cursor_y = VSTEP
    self.weight = "normal"
    self.style = "roman"
    self.size=12
    for tok in tokens:
      self.token(tok)

  def word(self, word):
    font = tkinter.font.Font(
      size=self.size,
      weight=self.weight,
      slant=self.style
    )
    self.display_list.append(((self.cursor_x, self.cursor_y, word, font)))
    w = font.measure(word)
    self.cursor_x += w + font.measure(" ")
    if (self.cursor_x + w >= WIDTH-HSTEP):
      self.cursor_y += font.metrics("linespace") * 1.25 #1.25: line spacing
      self.cursor_x = HSTEP
    
  def token(self, tok):
    if isinstance(tok, Text):
      for word in tok.text.split():
        self.word(word)
    elif tok.tag == "i":
      self.style = "italic"
    elif tok.tag == "/i":
      self.style = "roman"
    elif tok.tag == "b":
      self.weight = "bold"
    elif tok.tag == "/b":
      self.weight = "normal"
    elif tok.tag == "small":
      self.size -=2
    elif tok.tag == "/small":
      self.size += 2
    elif tok.tag == "big":
      self.size += 4
    elif tok.tag == "/big":
      self.size -= 4

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

  # 저장된 위치를 기반으로 각 문자를 그림 - 화면 좌표만 고려
  def draw(self):
    self.canvas.delete("all")
    for x, y, word, font in self.display_list:
      if y > self.scroll + HEIGHT: continue # 창의 아래문자 건너뛰기
      if y + VSTEP < self.scroll: continue # 창의 위의 문자 건너뛰기
      self.canvas.create_text(x, y-self.scroll, text=word, anchor="nw")

  # 웹페이지 로드
  def load(self, url):
    body = url.request()
    tokens = lex(body)
    self.display_list = Layout(tokens).display_list
    self.draw()

  # 스크롤 
  def scrolldown(self, e):
    SCROLL_STEP = 100
    self.scroll += SCROLL_STEP
    self.draw()

# load 함수 실행
if __name__ == "__main__":
  import sys
  Browser().load(URL(sys.argv[1])) # sys.argv: 파이썬 스크립트 실행 시 전달되는 인자들의 리스트
  tkinter.mainloop()