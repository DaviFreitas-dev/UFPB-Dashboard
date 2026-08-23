import { BookOpenCheck, Info, Layers3, ShieldCheck } from "lucide-react";

import { formatDatePtBr, ratio } from "@/lib/dashboard";
import type { ProfileWorkspaceResult } from "@/lib/profile-workspace";
import styles from "./profile-workspace.module.css";

function cycleProgress(remainingHours: number, totalHours: number): number {
  return ratio(Math.max(totalHours - remainingHours, 0), totalHours);
}

export function SettingsWorkspace({ workspace, source }: ProfileWorkspaceResult) {
  const cycleBySubject = new Map(
    workspace.settings.cycle.map((item) => [item.discipline, item.remainingHours]),
  );
  const totalHours = workspace.settings.subjects.reduce((total, subject) => total + subject.hours, 0);
  const remainingHours = workspace.settings.cycle.reduce(
    (total, item) => total + item.remainingHours,
    0,
  );

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>Seu espaço de estudo</p>
          <h1>Configurações</h1>
          <p className={styles.intro}>Confira as disciplinas, os ambientes e o saldo do ciclo.</p>
        </div>
        <div className={styles.headerMeta}>
          <span>{formatDatePtBr(workspace.date)}</span>
          <span className={source === "api" ? styles.liveBadge : styles.demoBadge}>
            <span aria-hidden="true" />
            {source === "api" ? "Dados conectados" : "Demonstração"}
          </span>
        </div>
      </header>

      <aside className={styles.readOnlyNotice}>
        <Info aria-hidden="true" size={18} />
        <p>As alterações ainda são feitas no aplicativo atual do NEXO.</p>
      </aside>

      <section className={styles.settingStats} aria-label="Resumo do ciclo">
        <div>
          <span className={styles.summaryIcon}>
            <BookOpenCheck aria-hidden="true" size={20} />
          </span>
          <p>Disciplinas</p>
          <strong>{workspace.settings.subjects.length}</strong>
        </div>
        <div>
          <span className={styles.summaryIcon}>
            <Layers3 aria-hidden="true" size={20} />
          </span>
          <p>Carga do edital</p>
          <strong>{totalHours}h</strong>
        </div>
        <div>
          <span className={styles.summaryIcon}>
            <ShieldCheck aria-hidden="true" size={20} />
          </span>
          <p>Restante no ciclo</p>
          <strong>{remainingHours}h</strong>
        </div>
      </section>

      <section className={styles.section} aria-labelledby="subjects-heading">
        <div className={styles.sectionHeading}>
          <div>
            <p>Edital</p>
            <h2 id="subjects-heading">Disciplinas e ambiente</h2>
          </div>
          <span>{workspace.settings.subjects.length}</span>
        </div>
        <div className={styles.subjectPanel}>
          {workspace.settings.subjects.map((subject) => {
            const remaining = cycleBySubject.get(subject.discipline) ?? subject.hours;
            const completed = cycleProgress(remaining, subject.hours);

            return (
              <article className={styles.subjectRow} key={subject.discipline}>
                <div className={styles.subjectMain}>
                  <strong>{subject.discipline}</strong>
                  <span>{subject.environment}</span>
                </div>
                <div className={styles.subjectProgress}>
                  <div>
                    <span>Ciclo</span>
                    <strong>{Math.max(remaining, 0)}h restantes</strong>
                  </div>
                  <div className={styles.progressTrack} aria-hidden="true">
                    <span style={{ width: `${completed * 100}%` }} />
                  </div>
                </div>
                <span className={styles.hoursTag}>{subject.hours}h</span>
              </article>
            );
          })}
        </div>
      </section>

      <section className={styles.environments} aria-labelledby="environments-heading">
        <div>
          <p className={styles.eyebrow}>Ambientes disponíveis</p>
          <h2 id="environments-heading">Onde estudar</h2>
        </div>
        <div className={styles.environmentList}>
          {workspace.settings.environments.map((environment) => (
            <span key={environment}>{environment}</span>
          ))}
        </div>
      </section>
    </div>
  );
}
