"""Generator prompts for Goethe-Zertifikat A2 Hören, Teil 1-4."""

_COMMON = """
Everything you write is simple A2 German: short sentences, everyday words, present and perfect
tense. The script is what the student HEARS (it is turned into audio); write it as natural
spoken German, without stage directions, sound effects or text in brackets. Give every speaker
a consistent name or role and gender. The questions must be answerable only by listening: the
student never sees the script.

Also list the most useful A2 vocabulary that occurs in the script (vocabulary), with article
and plural for nouns and an English translation."""

TEIL1 = """You write Goethe-Zertifikat A2 Hören Teil 1 exercises.

Teil 1 has five separate short listening texts (item_number 1-5), each played twice: everyday
announcements and messages, e.g. a message on an answering machine, an announcement at a
station or in a shop, a short radio notice, a weather report. Each text has 1-6 lines.
For each text write one question with exactly 3 options. Exactly one option is correct; the
two wrong options should be details that also appear in or near the text (a different time,
day, place, number or person), so the student must listen precisely. The context sentence
tells the student what they will hear, without giving the answer.""" + _COMMON

TEIL2 = """You write Goethe-Zertifikat A2 Hören Teil 2 exercises.

Teil 2 is one conversation between two people, played only once. One person talks about
plans or events across a series of time points: weekdays, months, dates, clock times or
similar (pick ONE kind per exercise). The student matches each time point to a picture.

Write:
- A Beispiel (example) time point with its correct picture, and five Aufgaben (aufgabe_number
  6-10), each with a different time point of the same kind, in the order they come up.
- Nine pictures with codes a-i: activities or events (e.g. swimming, a birthday, a doctor's
  visit), each shown as one emoji plus a short German caption. One picture answers the
  Beispiel, five answer the Aufgaben (each picture used at most once), and three are
  distractors that do not answer anything.
- In the dialogue, every time point label must be said exactly as you wrote it, and the
  keyword of each correct picture must be said near its time point. Make it a little tricky:
  mention one or two distractor activities too (e.g. something that was planned and then
  changed), but the final answer for each time point must be clear.""" + _COMMON

TEIL3 = """You write Goethe-Zertifikat A2 Hören Teil 3 exercises.

Teil 3 has five short dialogues (item_number 11-15), each played only once. For each, the
student answers one question by choosing one of three pictures (one emoji plus a short German
caption each). The trick of this Teil: the dialogue mentions ALL THREE pictured things, but
only one answers the question (the others are rejected, already done, too expensive, for
someone else, and so on). Each option's keyword must literally occur in its dialogue.""" + _COMMON

TEIL4 = """You write Goethe-Zertifikat A2 Hören Teil 4 exercises.

Teil 4 is one radio interview (played twice) between a presenter and a guest who talks about
their life, job or hobby. Write 10-30 lines. Then write five statements (number 16-20) in the
order the information comes up; for each the answer is "ja" (the interview says so) or "nein"
(the interview says something different). Use both answers. A "nein" statement should be close
to something said, but wrong in one clear detail.""" + _COMMON


def build_user_prompt(teil: int, topic: str | None, level: str) -> str:
    topic_line = f"Topic: {topic}" if topic else "Topic: pick an everyday A2 topic."
    return f"Write a {level} Hören Teil {teil} exercise.\n{topic_line}"
