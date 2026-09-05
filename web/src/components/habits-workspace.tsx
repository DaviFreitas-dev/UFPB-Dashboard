import { Check, Circle, Flame } from "lucide-react";

import { ratio } from "@/lib/dashboard";
import type { PersonalWorkspaceResult } from "@/lib/personal-workspace";
import { PersonalWorkspaceFrame } from "./personal-workspace-frame";
import {
  HabitControls,
  HabitCreateForm,
} from "./personal-actions/habit-controls";
import styles from "./personal-workspace.module.css";

type HabitsWorkspaceProps = PersonalWorkspaceResult & {
  canMutate: boolean;
  initialItemId: string;
};

export function HabitsWorkspace({
  workspace,
  source,
  canMutate,
  initialItemId,
}: HabitsWorkspaceProps) {
  const progress = Math.round(ratio(workspace.habits.completed, workspace.habits.total) * 100);

  return (
    <PersonalWorkspaceFrame
      date={workspace.date}
      intro="Acompanhe o que foi feito e a sequência de cada hábito."
      route="/habitos"
      source={source}
      title="Hábitos"
    >
      <section className={styles.summaryCard} aria-label="Resumo dos hábitos">
        <span className={styles.summaryIcon}><Flame aria-hidden="true" size={19} /></span>
        <div>
          <span>Ritmo de hoje</span>
          <strong>{workspace.habits.completed} de {workspace.habits.total} concluídos</strong>
          <p>
            {progress === 100
              ? "Todos os hábitos do dia foram concluídos."
              : `${workspace.habits.total - workspace.habits.completed} ainda em aberto.`}
          </p>
        </div>
        <strong className={styles.summaryValue}>{progress}%</strong>
      </section>

      {canMutate ? (
        <HabitCreateForm initialItemId={initialItemId} />
      ) : source === "api" ? (
        <p className={styles.writesUnavailable}>
          As alterações ainda não estão disponíveis nesta versão.
        </p>
      ) : null}

      <section className={styles.section}>
        <div className={styles.sectionHeading}>
          <h2>Hoje</h2>
          <span>
            {workspace.habits.total} {workspace.habits.total === 1 ? "hábito" : "hábitos"}
          </span>
        </div>
        {workspace.habits.items.length ? (
          <div className={styles.listPanel}>
            {workspace.habits.items.map((habit, index) => (
              <article className={habit.completed ? styles.itemDone : styles.item} key={`${habit.configId || habit.title}:${index}`}>
                <span className={styles.stateIcon} aria-label={habit.completed ? "Concluído" : "Pendente"}>
                  {habit.completed ? <Check aria-hidden="true" size={14} /> : <Circle aria-hidden="true" size={12} />}
                </span>
                <div>
                  <strong>{habit.title}</strong>
                  <span>{habit.streakDays} {habit.streakDays === 1 ? "dia seguido" : "dias seguidos"}</span>
                </div>
                <span className={habit.completed ? styles.donePill : styles.openPill}>
                  {habit.completed ? "Feito" : "Em aberto"}
                </span>
                <HabitControls
                  canMutate={source === "api" && canMutate}
                  date={workspace.date}
                  habit={habit}
                />
              </article>
            ))}
          </div>
        ) : <div className={styles.emptyState}><strong>Sem hábitos ativos</strong><span>Nada para acompanhar neste dia.</span></div>}
      </section>
    </PersonalWorkspaceFrame>
  );
}
