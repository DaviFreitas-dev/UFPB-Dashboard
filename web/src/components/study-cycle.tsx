import { CheckCircle2, Clock3, Layers3 } from "lucide-react";

import { formatDatePtBr, ratio } from "@/lib/dashboard";
import type { StudyWorkspaceResult } from "@/lib/study-workspace";
import styles from "./study-workspace.module.css";

function SourceBadge({ source }: Pick<StudyWorkspaceResult, "source">) {
  return (
    <span className={source === "api" ? styles.liveBadge : styles.demoBadge}>
      <span aria-hidden="true" />
      {source === "api" ? "Dados conectados" : "Demonstração"}
    </span>
  );
}

export function StudyCycle({ studies, source }: StudyWorkspaceResult) {
  const { cycle } = studies;
  const summary = [
    { label: "Planejado", value: `${cycle.totalHours}h`, icon: Layers3 },
    { label: "Concluído", value: `${cycle.completedHours}h`, icon: CheckCircle2 },
    { label: "Restante", value: `${cycle.remainingHours}h`, icon: Clock3 },
  ];

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>Ritmo de estudo</p>
          <h1>Ciclo</h1>
          <p className={styles.intro}>Veja o avanço e o saldo de cada matéria.</p>
        </div>
        <div className={styles.headerMeta}>
          <span>{formatDatePtBr(studies.date)}</span>
          <SourceBadge source={source} />
        </div>
      </header>

      <section className={styles.cycleHero} aria-label="Progresso do ciclo">
        <div>
          <span>Progresso do ciclo</span>
          <strong>{Math.round(ratio(cycle.completedHours, cycle.totalHours) * 100)}%</strong>
          <p>{cycle.completedHours}h concluídas de {cycle.totalHours}h planejadas</p>
        </div>
        <div className={styles.heroTrack} aria-hidden="true">
          <span style={{ width: `${ratio(cycle.completedHours, cycle.totalHours) * 100}%` }} />
        </div>
      </section>

      <section className={styles.summaryStrip} aria-label="Resumo do ciclo">
        {summary.map(({ label, value, icon: Icon }) => (
          <div className={styles.summaryItem} key={label}>
            <Icon aria-hidden="true" size={17} />
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </section>

      <section className={styles.section}>
        <div className={styles.sectionHeading}>
          <div>
            <h2>Matérias do ciclo</h2>
            <p>{cycle.subjects.length} frentes acompanhadas</p>
          </div>
        </div>
        <div className={styles.subjectList}>
          {cycle.subjects.length ? cycle.subjects.map((item) => (
            <article className={styles.subjectRow} key={item.id}>
              <div className={styles.subjectTitle}>
                <strong>{item.subject}</strong>
                <span>{item.environment}</span>
                {item.legacy ? <small>Registro legado</small> : null}
              </div>
              <div className={styles.subjectProgress}>
                <div className={styles.progressTrack} aria-hidden="true">
                  <span style={{ width: `${ratio(item.completedHours, item.plannedHours) * 100}%` }} />
                </div>
                <span>{item.completedHours}h / {item.plannedHours}h</span>
              </div>
              <strong className={styles.remaining}>{item.remainingHours}h <small>restantes</small></strong>
            </article>
          )) : <p className={styles.empty}>Nenhuma matéria está disponível no ciclo.</p>}
        </div>
      </section>
    </div>
  );
}
