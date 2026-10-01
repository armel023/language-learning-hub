import { createBrowserRouter } from "react-router-dom";

import { App } from "../App";
import { ComingSoonPage } from "./ComingSoonPage";
import { FlashcardAddPage } from "./flashcards/FlashcardAddPage";
import { FlashcardListPage } from "./flashcards/FlashcardListPage";
import { FlashcardStudyPage } from "./flashcards/FlashcardStudyPage";
import { FlashcardUploadPage } from "./flashcards/FlashcardUploadPage";
import { LesenHomePage } from "./lesen/LesenHomePage";

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
      { path: "hoeren", element: <ComingSoonPage skill="Hören" /> },
      { path: "schreiben", element: <ComingSoonPage skill="Schreiben" /> },
      { path: "sprechen", element: <ComingSoonPage skill="Sprechen" /> },
    ],
  },
]);
