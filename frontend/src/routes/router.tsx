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
import { HoerenHomePage } from "./hoeren/HoerenHomePage";
import { HoerenTeil1Page } from "./hoeren/HoerenTeil1Page";
import { HoerenTeil2Page } from "./hoeren/HoerenTeil2Page";
import { HoerenTeil3Page } from "./hoeren/HoerenTeil3Page";
import { HoerenTeil4Page } from "./hoeren/HoerenTeil4Page";
import { SchreibenHomePage } from "./schreiben/SchreibenHomePage";
import { SchreibenTeilPage } from "./schreiben/SchreibenTeilPage";

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
      { path: "hoeren", element: <HoerenHomePage /> },
      { path: "hoeren/teil1", element: <HoerenTeil1Page /> },
      { path: "hoeren/teil2", element: <HoerenTeil2Page /> },
      { path: "hoeren/teil3", element: <HoerenTeil3Page /> },
      { path: "hoeren/teil4", element: <HoerenTeil4Page /> },
      { path: "schreiben", element: <SchreibenHomePage /> },
      { path: "schreiben/teil1", element: <SchreibenTeilPage key="teil1" teil={1} /> },
      { path: "schreiben/teil2", element: <SchreibenTeilPage key="teil2" teil={2} /> },
      { path: "sprechen", element: <ComingSoonPage skill="Sprechen" /> },
    ],
  },
]);
