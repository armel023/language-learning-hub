import { createBrowserRouter } from "react-router-dom";

import { App } from "../App";
import { ComingSoonPage } from "./ComingSoonPage";
import { FlashcardAddPage } from "./flashcards/FlashcardAddPage";
import { FlashcardListPage } from "./flashcards/FlashcardListPage";
import { FlashcardStudyPage } from "./flashcards/FlashcardStudyPage";
import { FlashcardUploadPage } from "./flashcards/FlashcardUploadPage";
import { LesenHomePage } from "./lesen/LesenHomePage";
import { Teil1Page } from "./lesen/Teil1Page";
import { Teil2Page } from "./lesen/Teil2Page";
import { Teil3Page } from "./lesen/Teil3Page";
import { Teil4Page } from "./lesen/Teil4Page";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <FlashcardListPage /> },
      { path: "flashcards", element: <FlashcardListPage /> },
      { path: "flashcards/add", element: <FlashcardAddPage /> },
      { path: "flashcards/upload", element: <FlashcardUploadPage /> },
      { path: "flashcards/study", element: <FlashcardStudyPage /> },
      { path: "lesen", element: <LesenHomePage /> },
      { path: "lesen/teil1", element: <Teil1Page /> },
      { path: "lesen/teil2", element: <Teil2Page /> },
      { path: "lesen/teil3", element: <Teil3Page /> },
      { path: "lesen/teil4", element: <Teil4Page /> },
      { path: "hoeren", element: <ComingSoonPage skill="Hören" /> },
      { path: "schreiben", element: <ComingSoonPage skill="Schreiben" /> },
      { path: "sprechen", element: <ComingSoonPage skill="Sprechen" /> },
    ],
  },
]);
