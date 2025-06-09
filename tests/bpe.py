from collections import Counter
from functools import lru_cache
from typing import Dict, List, Tuple

import regex


def replace_pair_with_single(source: Tuple[int], target: Tuple[int], replacement: int) -> Tuple[int]:
    result = []
    i = 0
    while i < len(source):
        if i < len(source) - 1 and (source[i], source[i + 1]) == target:
            result.append(replacement)
            i += 2
        else:
            result.append(source[i])
            i += 1
    return tuple(result)


def count_byte_pair(unicode_counter: Dict[Tuple[int], int]) -> Dict[Tuple[int], int]:
    out = {}

    for codes, count in unicode_counter.items():
        for i in range(len(codes) - 1):
            byte_pair = codes[i : i + 2]
            out[byte_pair] = out.get(byte_pair, 0) + count

    return out


def get_most_frequent_byte_pair(byte_pair_counter: Dict[Tuple[int, int], int]) -> (Tuple[int, int], int):
    return max(byte_pair_counter.items(), key=lambda item: (item[1], item[0]))


class BytePairEncodingTokenizer:
    FIRST_CUSTOM_TOKEN = 256

    vocab = {}
    reversed_vocab = {}
    special_text_pattern = ""
    reversed_special_vocab = {}
    special_vocab = {}

    def __init__(self, vocab: Dict[int, Tuple[int, int]] = None, special_texts: List[str] = None):
        self.vocab = vocab or {}
        self.reversed_vocab = {pair: token for token, pair in self.vocab.items()}
        self.special_text_pattern = r"|".join(special_texts)

        for i, text in enumerate(special_texts):
            custom_token = self.FIRST_CUSTOM_TOKEN + i
            self.reversed_special_vocab[text] = custom_token
            self.special_vocab[custom_token] = text.encode("utf-8")

    def train(
        self,
        training_text: str,
        max_vocab_size: int = 10_000,
        min_freq: int = 2,
        max_iter: int = 100_000,
    ) -> Dict[int, Tuple[int, int]]:
        PAT = r"""'(?:[sdmt]|ll|ve|re)| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"""
        pretokens = regex.findall(PAT, regex.sub(self.special_text_pattern, "", training_text))
        pretoken_counter = Counter(pretokens)
        unicode_counter = {tuple(pretoken.encode("utf-8")): count for pretoken, count in pretoken_counter.items()}
        existing_token_count = self.FIRST_CUSTOM_TOKEN + len(self.special_vocab)
        next_custom_token = existing_token_count + len(self.vocab)

        for _ in range(max_iter):
            if len(self.vocab) + existing_token_count >= max_vocab_size:
                break

            byte_pair_counter = count_byte_pair(unicode_counter)
            (most_freq_byte_pair, most_freq) = get_most_frequent_byte_pair(byte_pair_counter)

            if most_freq < min_freq:
                break

            self.vocab[next_custom_token] = most_freq_byte_pair

            unicode_counter = {
                replace_pair_with_single(codes, most_freq_byte_pair, next_custom_token): count
                for codes, count in unicode_counter.items()
            }

            next_custom_token += 1

        self.reversed_vocab = {pair: token for token, pair in self.vocab.items()}
        return self.vocab

    def encode(self, text: str) -> List[int]:
        tokens = []
        substrings = regex.split(f"({self.special_text_pattern})", text) if self.special_text_pattern else [text]

        for substring in substrings:
            if not substring:
                continue
            if substring in self.reversed_special_vocab:
                tokens.append(self.reversed_special_vocab[substring])
            else:
                tokens.extend(self.__encode_normal_text(substring))

        return tokens

    def __encode_normal_text(self, text: str) -> List[int]:
        stack: List[int] = []

        for code in text.encode("utf-8"):
            stack.append(code)

            while len(stack) >= 2 and (stack[-2], stack[-1]) in self.reversed_vocab:
                right = stack.pop()
                left = stack.pop()
                stack.append(self.reversed_vocab[(left, right)])

        return stack

    def decode(self, tokens: List[int]) -> str:
        @lru_cache(maxsize=10_000)
        def expand(token: int) -> Tuple[int]:
            if token not in self.vocab:
                return (token,)
            left, right = self.vocab[token]
            return expand(left) + expand(right)

        byte_unicodes = [
            bytes([int_unicode])
            for token in tokens
            for int_unicode in (self.special_vocab[token] if token in self.special_vocab else expand(token))
        ]

        return b"".join(byte_unicodes).decode("utf-8")


if __name__ == "__main__":
    training_text = """
Whores in this house
There's some whores in this house
There's some whores in this house
There's some whores in this house (hol' up)
I said certified freak, seven days a week
Wet ass pussy, make that pullout game weak, woo! (Ah)
Yeah, yeah, yeah, yeah
Yeah, you fucking with some wet ass pussy
Bring a bucket and a mop for this wet ass pussy
Give me everything you got for this wet ass pussy
Beat it up, nigga, catch a charge
Extra large, and extra hard
Put this pussy right in yo' face
Swipe your nose like a credit card
Hop on top, I want a ride
I do a kegel while it's inside
Spit in my mouth, look at my eyes
This pussy is wet, come take a dive
Tie me up like I'm surprised
Let's role-play, I wear a disguise
I want you to park that big Mack truck right in this little garage
Make it cream, make me scream
Out in public, make a scene
I don't cook, I don't clean
But let me tell you, I got this ring (ayy, ayy)
Gobble me, swallow me, drip down the side of me (yeah)
Quick, jump out 'fore you let it get inside of me (yeah)
I tell him where to put it, never tell him where I'm 'bout to be
I run down on him 'fore I have a nigga running me
Talk yo' shit, bite your lip
Ask for a car while you ride that dick (while you ride that dick)
You ain't never gotta fuck him for a thing
He already made his mind up 'fore he came
Now get your boots and your coat for this wet ass pussy
He bought a phone just for pictures of this wet ass pussy
Pay my tuition just to kiss me on this wet ass pussy
Now make it rain if you wanna see some wet ass pussy
Look, I need a hard hitter, I need a deep stroke
I need a Henny drink, I need a weed smoker
Not a garden snake, I need a king cobra
With a hook in it, hope it lean over
He got some money, then that's where I'm headed
Pussy A-1, just like his credit
He got a beard, well, I'm tryna wet it
I let him taste it, and now he diabetic
I don't wanna spit, I wanna gulp
I wanna gag, I wanna choke
I want you to touch that lil' dangly thing that swing in the back of my throat
My head game is fire, punani Dasani
It's going in dry, and it's coming out soggy
I ride on that thing like the cops is behind me (yuh, ah)
I spit on his mic' and now he tryna sign me, woo
Your honor, I'm a freak bitch, handcuffs, leashes
Switch my wig, make him feel like he cheating
Put him on his knees, give him some' to believe in
Never lost a fight, but I'm looking for a beating
In the food chain, I'm the one that eat ya
If he ate my ass, he's a bottom feeder
Big D stand for big demeanor
I could make ya bust before I ever meet ya
If it don't hang, then he can't bang
You can't hurt my feelings, but I like pain
If he fuck me and ask, "Whose is it?"
When I ride the dick, I'ma spell my name, ah
Yeah, yeah, yeah
Yeah, you fucking with some wet ass pussy
Bring a bucket and a mop for this wet ass pussy
Give me everything you got for this wet ass pussy
Now from the top, make it drop, that's some wet ass pussy
Now get a bucket and a mop, that's some wet ass pussy
I'm talking WAP, WAP, WAP, that's some wet ass pussy
Macaroni in a pot, that's some wet ass pussy, huh
There's some whores in this house
There's some whores in this house
There's some whores in this house
There's some whores in this house
There's some whores in this house
There's some whores in this house
There's some whores in this house
There's some whores in this house
There's some whores in this house
There's some whores in this house
There's some whores in this house

I'm the mother Fucking top madam
삼촌들 용돈 뺏는 깡패
그걸로 popping bottle 샴페인
사뿐히 밟아 빨간 carpet
남자들 숨을 참네
멋진 척 참 내
니 남친 나를 탐내
cuz im the motherfucking top madam
센 티만 계속 냈던
넌 정말 nothing
까고 보니 별 거 없어
넌 정말 nothing
어깨 힘 빼고 이제는 배워
완전히 정복해 여자판 나폴레옹
이제 씹을 거리 없지
단물 빠진 껌을
억지로 질겅 씹어 봐라
가출해 니 턱주가리
가슴에 턱 붙여 빨리
고개 끄덕
everybody bounce
im sick of them puss
puss puss
bitch you a freaking puss puss
puss puss
bitch you a freaking puss puss
im the mofucking top man
니네 비지니스는 다음에
imma make her super star man
cuz im a motherfuking top man
내가 뜰 줄 몰랐지
금방 질 줄 알았는데 모두 놀랐지
완전체로 돌아왔네
아이언맨은 피융
from the Rock Bottom 빼고
전부 fake shit
all the motherfuckers pissed off
왜냐면 그년 나를 위한 비서
아니 그년 나를 위한 시소
아니아니 그년 나를 위한 칙쇼
beast mode
우린 전국 돌며 니네들 삥 뜯어
매일이 payday
그 덤으로 highway 를 타며
학준 형과 vacay
만들어 방방곡곡
one hunit thousand babies
cuz you are my freaking Puss Puss
puss puss
cuz you are my freaking puss puss
puss puss
cuz you are my freaking puss puss
yes im the real bad man aye aye
yes im the real bad madam aye aye
im the motherfucking top man
im the motherfucking top madam
im the motherfucking top man
bitch you a fucking puss puss
puss puss
Bitch you a freaking puss puss
puss puss
Bitch you a freaking puss puss
bitch you a fucking puss
"""
    test_text = "I'm the mother Fucking top madam<|endoftext|>"
    bpe = BytePairEncodingTokenizer(special_texts=["<|endoftext|>"])
    bpe.train(training_text, max_vocab_size=500)

    assert bpe.vocab.get(500) is None
    assert bpe.decode(bpe.encode(test_text)) == test_text
    assert bpe.decode(test_text.encode("utf-8")) == test_text
