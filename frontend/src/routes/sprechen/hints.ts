/** Useful phrases (Redemittel) per Teil, shown behind the Hint button. Static on purpose: no AI call,
 * instant, and they never give away the partner's card. */
export const HINTS: Record<number, { title: string; phrases: string[] }[]> = {
  1: [
    {
      title: "Fragen stellen",
      phrases: [
        "Wann hast du Geburtstag?",
        "Wo wohnst du?",
        "Was bist du von Beruf? / Was machst du beruflich?",
        "Was ist dein Hobby? / Was machst du gern in deiner Freizeit?",
        "Welche Musik hörst du gern?",
        "Hast du Geschwister?",
      ],
    },
    {
      title: "Antworten (2–3 Sätze)",
      phrases: [
        "Ich wohne in … . Die Stadt ist … . Ich wohne dort seit … .",
        "Mein Hobby ist … . Ich mache das (oft / am Wochenende) mit … .",
        "Ich arbeite als … . Die Arbeit ist … , aber … .",
      ],
    },
  ],
  2: [
    {
      title: "Anfangen und verbinden",
      phrases: [
        "Ich möchte etwas über … erzählen.",
        "Am Wochenende … / Meistens … / Manchmal …",
        "Zuerst … , dann … , danach …",
        "Das mache ich gern, weil …",
        "Außerdem … / Aber …",
      ],
    },
    {
      title: "Abschließen",
      phrases: ["Das ist alles. Danke.", "Das war's, vielen Dank."],
    },
  ],
  3: [
    {
      title: "Vorschlagen",
      phrases: [
        "Hast du am … um … Uhr Zeit?",
        "Wie wäre es mit …? / Wollen wir …?",
        "Ich schlage vor, dass wir …",
        "Was meinst du?",
      ],
    },
    {
      title: "Reagieren",
      phrases: [
        "Ja, das passt mir gut. / Gute Idee!",
        "Um … Uhr kann ich leider nicht, da muss ich …",
        "Nein, das geht leider nicht. Aber wie wäre es um …?",
        "Okay, dann treffen wir uns um … Uhr.",
      ],
    },
  ],
};
