import { Check, Circle, ListChecks } from "lucide-react";

import { ratio } from "@/lib/dashboard";
import type { PersonalWorkspaceResult } from "@/lib/personal-workspace";
import { PersonalWorkspaceFrame } from "./personal-workspace-frame";
import { TaskCreateForm } from "./task-create-form";
import styles from "./personal-workspace.module.css";

type TasksWorkspaceProps = PersonalWorkspaceResult & {
  canMutate: boolean;
  initialItemId: string;
};

export function TasksWorkspace({
  workspace,
  source,
  canMutate,
  initialItemId,
}: TasksWorkspaceProps) {
  const progress = Math.round(ratio(workspace.tasks.completed, workspace.tasks.total) * 100);
  const remaining = Math.max(workspace.tasks.total - workspace.tasks.completed, 0);

  return (
    <PersonalWorkspaceFrame
      date={workspace.date}
      intro="O que merece sua atenção hoje."
      route="/tarefas"
      source={source}
      title="Tarefas"
    >
      <section className={styles.summaryCard} aria-label="Resumo das tarefas">
        <span className={styles.summaryIcon}><ListChecks aria-hidden="true" size={19} /></span>
        <div>
          <span>Progresso do dia</span>
          <strong>{workspace.tasks.completed} de {workspace.tasks.total} concluídas</strong>
          <p>{remaining ? `${remaining} ${remaining === 1 ? "tarefa pendente" : "tarefas pendentes"}.` : "Tudo concluído por aqui."}</p>
        </div>
        <strong className={styles.summaryValue}>{progress}%</strong>
      </section>

      {canMutate ? (
        <TaskCreateForm
          initialItemId={initialItemId}
          selectedDate={workspace.date}
        />
      ) : null}

      <section className={styles.section}>
        <div className={styles.sectionHeading}>
          <h2>Agenda do dia</h2>
          <span>
            {workspace.tasks.total} {workspace.tasks.total === 1 ? "item" : "itens"}
          </span>
        </div>
        {workspace.tasks.items.length ? (
          <div className={styles.listPanel}>
            {workspace.tasks.items.map((task) => (
              <article className={task.completed ? styles.itemDone : styles.item} key={task.id}>
                <span className={styles.stateIcon} aria-label={task.completed ? "Concluída" : "Pendente"}>
                  {task.completed ? <Check aria-hidden="true" size={14} /> : <Circle aria-hidden="true" size={12} />}
                </span>
                <div>
                  <strong>{task.title}</strong>
                  <span>{task.category}</span>
                </div>
                <span className={task.completed ? styles.donePill : styles.openPill}>
                  {task.completed ? "Concluída" : "Pendente"}
                </span>
              </article>
            ))}
          </div>
        ) : <EmptyState text="Nenhuma tarefa para este dia." />}
      </section>
    </PersonalWorkspaceFrame>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className={styles.emptyState}><strong>Agenda livre</strong><span>{text}</span></div>;
}
