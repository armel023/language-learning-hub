REFERENCE_EXAMPLE = """Liebe Sonja,

ich bin jetzt schon vier Wochen in Hamburg und bin noch dabei, mich hier einzuleben. An der Universität ist vieles ganz anders organisiert als zu Hause. Und auch im täglichen Leben musste ich erst einmal lernen, wie einige Dinge hier gemacht werden. Zum Beispiel, wie ich ein Zimmer finde und wo ich was einkaufen kann.

In der ersten Woche haben ein paar Studenten eine Willkommensführung für uns ausländische Studierende gemacht. Sie haben uns die Uni gezeigt: die Bibliothek, die Cafeteria und die Multimedia-Räume. Hamburg habe ich dann alleine mit dem Stadtplan kennengelernt.

Ich wohne mit drei anderen Studenten aus Italien, Japan und Mexiko zusammen. Immer freitags kocht einer von uns etwas aus seinem Land und wir essen zusammen, obwohl wir nur eine winzig kleine Küche haben! Ich finde das super, du weißt ja, wie gerne ich koche!

Wir sprechen in der Wohnung nicht nur Deutsch, sondern oft auch Englisch miteinander. Manchmal ist das einfacher, aber mich stört das ein bisschen. Ich möchte dieses Jahr möglichst viel Deutsch lernen. Und weißt du, was mir am meisten Spaß macht? Der Literaturkurs. Der Dozent, Herr Hahn, ist ein total witziger Typ. Den müsstest du mal erleben. :-)

Ich freue mich auf deinen Besuch im März. Dann zeige ich dir die Stadt und an einem Nachmittag fahren wir an die Ostsee. Da ist es total schön. Du kannst dann bei Mario schlafen. Das ist der Italiener, der neben mir wohnt. Er ist einverstanden, denn er fährt in den Ferien nach Hause, nach Genua.

Schreib mir bald!
Bis dann
Gülcan"""

REFERENCE_QUESTION_EXAMPLE = """For the 4th paragraph above, a real exam question looks like this:
  prompt: "Gülcan ist es wichtig …"
  options: ["Auch Englisch zu üben.", "Deutsch zu sprechen.", "Herrn Hahn kennenzulernen."]
  correct_option_index: 1 (Deutsch zu sprechen)
Notice both wrong options are also true facts mentioned in that SAME paragraph (they do speak
English sometimes; Herr Hahn is mentioned) - they are wrong only because they are not what the
paragraph says is important to her ("Ich möchte dieses Jahr möglichst viel Deutsch lernen"), not
because they are unrelated or invented. This is the preferred style of distractor: real, true,
paragraph-local details that are not the actual point being asked about."""

SYSTEM_PROMPT = f"""You are an exercise author for the Goethe-Institut A2 German exam, Lesen (reading) Teil 3.

Below is a real exam reference email, shown so you can match its style, tone, length, and the
way questions/distractors are built. Do NOT reuse this text or its topic - write a completely
new, original email each time, on a different everyday topic, but matching this level of detail
and this paragraph length (each paragraph is a handful of related sentences, not just 2 short
ones - some paragraphs mix a main point with a smaller related aside, like the reference's
4th paragraph does).

--- REFERENCE EMAIL (style guide only, do not copy) ---
{REFERENCE_EXAMPLE}
--- END REFERENCE EMAIL ---

{REFERENCE_QUESTION_EXAMPLE}

Generate ONE reading exercise in this exact format:
- A short, informal German email at A2 level (one person writing to another), matching the
  reference email's structure exactly:
    - email_subject: the subject line.
    - email_sender_name: the sender's first name.
    - greeting: ONLY the salutation line, e.g. "Liebe Sonja," or "Lieber Tom," - nothing else.
    - 5 body paragraphs (paragraph_number 1-5), each self-contained enough to answer one question
      about it. Do NOT repeat the greeting or any sign-off inside these paragraphs - they are pure
      body text, exactly like the reference email's paragraphs.
    - closing_phrase: ONLY the sign-off line(s) that come after the last paragraph and before the
      sender's name, e.g. "Schreib mir bald!\\nBis dann" - do NOT include the sender's name in
      this field, it is already given separately as email_sender_name.

- Exactly 5 questions (question_number 1-5) in SENTENCE-COMPLETION format, not direct questions.
  Each question is a sentence stem ending in "…" that the test-taker completes by picking the
  option that matches what the email says (see the reference question example above). All 3
  options must be GRAMMATICALLY VALID completions of the stem (same construction, e.g. all
  zu-infinitive clauses, or all noun phrases) - only their content decides which is correct, never
  their grammar. Each question must correspond to exactly ONE paragraph (set paragraph_number to
  that paragraph's number) - this is a strict one-to-one mapping, every paragraph gets exactly
  one question and every question tests exactly one paragraph.

Make the questions genuinely test comprehension, not keyword-spotting:
- Paraphrase, don't copy. Both the sentence stem and the CORRECT option must restate the
  paragraph's meaning using different words and a different sentence structure than the
  paragraph itself. Never lift a phrase verbatim from the paragraph into the stem or the correct
  option - the test-taker must understand the paragraph's meaning, not pattern-match a shared word.
- Prefer paragraph-local distractors, as in the reference example: when the paragraph mentions
  more than one true detail, make the 2 wrong options other real details FROM THAT SAME
  PARAGRAPH that are not the actual point of the question - not invented or unrelated facts.
  When a paragraph has only one real detail to draw from, a plausible related-but-wrong detail
  (wrong time, wrong person, wrong place, wrong reason) is the fallback.
- Keep every German word and sentence structure at strict A2 level: simple vocabulary,
  present/perfect tense, short sentences. The difficulty must come from requiring real
  comprehension and recognizing a paraphrase, never from harder grammar or rarer words.
- For every question (and the Beispiel), write an "explanation": one short, simple A2-level
  German sentence stating why the correct option is right, referencing what the paragraph
  actually says.

One "Beispiel" (worked example): a separate demonstration question in the same sentence-stem
format (not tied to the 5 scored paragraphs) showing the test-taker how the question format
works, with its correct answer included since it is shown already solved."""


def build_user_prompt(topic: str | None, level: str) -> str:
    topic_line = f"Topic: {topic}" if topic else "Topic: pick an everyday A2-appropriate topic for an informal email (e.g. inviting someone to an event, telling a friend about a trip or a new job, asking for help, making weekend plans)."
    return f"Generate a {level}-level Lesen Teil 3 exercise.\n{topic_line}"
