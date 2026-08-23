import { BookOpen, Check } from "lucide-react";

import type { PersonalWorkspaceResult } from "@/lib/personal-workspace";
import { PersonalWorkspaceFrame } from "./personal-workspace-frame";
import styles from "./personal-workspace.module.css";

export function ReadingWorkspace({ workspace, source }: PersonalWorkspaceResult) {
  const inProgress = workspace.reading.items.filter((book) => book.status === "Lendo").length;

  return (
    <PersonalWorkspaceFrame
      date={workspace.date}
      intro="Acompanhe seus livros sem perder o fio."
      route="/leitura"
      showDateNavigation={false}
      source={source}
      title="Leitura"
    >
      <section className={styles.summaryCard} aria-label="Resumo de leitura">
        <span className={styles.summaryIcon}><BookOpen aria-hidden="true" size={19} /></span>
        <div>
          <span>Biblioteca</span>
          <strong>{workspace.reading.items.length} {workspace.reading.items.length === 1 ? "livro" : "livros"} acompanhados</strong>
          <p>{inProgress ? `${inProgress} ${inProgress === 1 ? "leitura em andamento" : "leituras em andamento"}.` : "Nenhuma leitura em andamento."}</p>
        </div>
      </section>

      <section className={styles.section}>
        <div className={styles.sectionHeading}>
          <h2>Biblioteca</h2>
          <span>
            {workspace.reading.items.length} {workspace.reading.items.length === 1 ? "título" : "títulos"}
          </span>
        </div>
        {workspace.reading.items.length ? (
          <div className={styles.readingGrid}>
            {workspace.reading.items.map((book) => {
              const progress = Math.min(Math.max(book.progress, 0), 1);
              return (
                <article className={styles.bookCard} key={book.id}>
                  <div className={styles.bookTopline}>
                    <span className={book.status === "Concluído" ? styles.donePill : styles.openPill}>
                      {book.status}
                    </span>
                    {book.status === "Concluído" ? <Check aria-label="Concluído" size={16} /> : null}
                  </div>
                  <strong>{book.title}</strong>
                  <p>{book.author || "Autor não informado"}</p>
                  <div className={styles.progressTrack} aria-label={`${Math.round(progress * 100)}% concluído`}>
                    <span style={{ width: `${progress * 100}%` }} />
                  </div>
                  <div className={styles.bookMeta}>
                    <span>{book.currentPage} de {book.totalPages} páginas</span>
                    <span>{book.remainingTarget} {book.remainingTarget === 1 ? "página" : "páginas"} na meta</span>
                  </div>
                </article>
              );
            })}
          </div>
        ) : <div className={styles.emptyState}><strong>Biblioteca vazia</strong><span>Nenhum livro cadastrado ainda.</span></div>}
      </section>
    </PersonalWorkspaceFrame>
  );
}
