import { Award, BadgeCheck, LockKeyhole } from "lucide-react";

import { formatDatePtBr, ratio } from "@/lib/dashboard";
import {
  achievementFootnote,
  type ProfileWorkspaceResult,
} from "@/lib/profile-workspace";
import styles from "./profile-workspace.module.css";

export function AchievementsWorkspace({ workspace, source }: ProfileWorkspaceResult) {
  const progress = ratio(workspace.achievements.unlocked, workspace.achievements.total);
  const remaining = Math.max(workspace.achievements.total - workspace.achievements.unlocked, 0);

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>Progresso pessoal</p>
          <h1>Conquistas</h1>
          <p className={styles.intro}>Marcos do seu histórico de estudos.</p>
        </div>
        <div className={styles.headerMeta}>
          <span>{formatDatePtBr(workspace.date)}</span>
          <span className={source === "api" ? styles.liveBadge : styles.demoBadge}>
            <span aria-hidden="true" />
            {source === "api" ? "Dados conectados" : "Demonstração"}
          </span>
        </div>
      </header>

      <section className={styles.achievementSummary} aria-label="Progresso das conquistas">
        <span className={styles.summaryIcon}>
          <Award aria-hidden="true" size={22} />
        </span>
        <div className={styles.summaryCopy}>
          <span>Conquistas liberadas</span>
          <strong>
            {workspace.achievements.unlocked} de {workspace.achievements.total}
          </strong>
        </div>
        <div className={styles.summaryProgress}>
          <div className={styles.progressTrack} aria-hidden="true">
            <span style={{ width: `${progress * 100}%` }} />
          </div>
          <small>
            {remaining ? `${remaining} ${remaining === 1 ? "marco restante" : "marcos restantes"}` : "Todos os marcos foram concluídos"}
          </small>
        </div>
      </section>

      <section className={styles.section} aria-labelledby="achievements-heading">
        <div className={styles.sectionHeading}>
          <div>
            <p>Seu percurso</p>
            <h2 id="achievements-heading">Marcos</h2>
          </div>
          <span>{workspace.achievements.total}</span>
        </div>
        <div className={styles.achievementGrid}>
          {workspace.achievements.items.map((achievement) => (
            <article
              className={achievement.unlocked ? styles.achievementCard : styles.achievementCardLocked}
              key={achievement.id}
            >
              <span className={styles.achievementIcon}>
                {achievement.unlocked ? (
                  <BadgeCheck aria-hidden="true" size={19} />
                ) : (
                  <LockKeyhole aria-hidden="true" size={18} />
                )}
              </span>
              <div className={styles.achievementCopy}>
                <div>
                  <strong>{achievement.title}</strong>
                  <span className={achievement.unlocked ? styles.statusDone : styles.statusLocked}>
                    {achievement.unlocked ? "Concluída" : "Bloqueada"}
                  </span>
                </div>
                <p>{achievement.description}</p>
                <small>{achievementFootnote(achievement)}</small>
              </div>
            </article>
          ))}
        </div>
      </section>

    </div>
  );
}
