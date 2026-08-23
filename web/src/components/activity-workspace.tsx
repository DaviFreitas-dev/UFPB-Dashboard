import { Check, Circle, Dumbbell } from "lucide-react";

import type { PersonalWorkspaceResult } from "@/lib/personal-workspace";
import { PersonalWorkspaceFrame } from "./personal-workspace-frame";
import styles from "./personal-workspace.module.css";

export function ActivityWorkspace({ workspace, source }: PersonalWorkspaceResult) {
  const completed = workspace.activity.items.filter((item) => item.completed).length;

  return (
    <PersonalWorkspaceFrame
      date={workspace.date}
      intro="Veja as atividades físicas registradas no dia."
      route="/atividade"
      source={source}
      title="Atividade"
    >
      <section className={styles.summaryCard} aria-label="Resumo de atividade física">
        <span className={styles.summaryIcon}><Dumbbell aria-hidden="true" size={19} /></span>
        <div>
          <span>Atividade física</span>
          <strong>{completed} {completed === 1 ? "registro concluído" : "registros concluídos"}</strong>
          <p>{completed ? "Seu movimento de hoje está registrado." : "Sem atividade concluída neste dia."}</p>
        </div>
      </section>

      <section className={styles.section}>
        <div className={styles.sectionHeading}>
          <h2>Registros do dia</h2>
          <span>
            {workspace.activity.items.length} {workspace.activity.items.length === 1 ? "registro" : "registros"}
          </span>
        </div>
        {workspace.activity.items.length ? (
          <div className={styles.listPanel}>
            {workspace.activity.items.map((item) => (
              <article className={item.completed ? styles.itemDone : styles.item} key={item.id}>
                <span className={styles.stateIcon} aria-label={item.completed ? "Concluída" : "Pendente"}>
                  {item.completed ? <Check aria-hidden="true" size={14} /> : <Circle aria-hidden="true" size={12} />}
                </span>
                <div><strong>{item.type}</strong><span>Atividade física</span></div>
                <span className={item.completed ? styles.donePill : styles.openPill}>
                  {item.completed ? "Registrada" : "Pendente"}
                </span>
              </article>
            ))}
          </div>
        ) : <div className={styles.emptyState}><strong>Sem registros</strong><span>Nenhuma atividade para este dia.</span></div>}
      </section>
    </PersonalWorkspaceFrame>
  );
}
