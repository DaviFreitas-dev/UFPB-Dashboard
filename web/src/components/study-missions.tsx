"use client";

import { useMemo, useState } from "react";
import { Clock3, Shuffle, Sparkles } from "lucide-react";

import { formatDatePtBr } from "@/lib/dashboard";
import {
  drawLocalMission,
  type MissionEnvironment,
  type StudyWorkspaceResult,
} from "@/lib/study-workspace";
import styles from "./study-workspace.module.css";

const environments: MissionEnvironment[] = ["Ambos", "Mesa", "Transporte"];

export function StudyMissions({ studies, source }: StudyWorkspaceResult) {
  const [environment, setEnvironment] = useState<MissionEnvironment>("Ambos");
  const [duration, setDuration] = useState(studies.missions.durationOptions[0] ?? 1);
  const [seed, setSeed] = useState(0);

  const mission = useMemo(
    () => seed ? drawLocalMission(studies.missions.subjects, environment, duration) : [],
    [duration, environment, seed, studies.missions.subjects],
  );
  const plannedHours = mission.reduce((total, item) => total + item.hours, 0);
  const visibleSubjects = studies.missions.subjects.filter(
    (item) => environment === "Ambos" || item.environment === "Ambos" || item.environment === environment,
  );

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>Próxima sessão</p>
          <h1>Missões</h1>
          <p className={styles.intro}>Escolha o ambiente e a duração da próxima sessão.</p>
        </div>
        <div className={styles.headerMeta}>
          <span>{formatDatePtBr(studies.date)}</span>
          <span className={source === "api" ? styles.liveBadge : styles.demoBadge}>
            <span aria-hidden="true" />
            {source === "api" ? "Dados conectados" : "Demonstração"}
          </span>
        </div>
      </header>

      <section className={styles.missionHero}>
        <div>
          <span>Disponibilidade atual</span>
          <strong>{studies.missions.totalAvailableHours}h</strong>
          <p>O sorteio é só uma sugestão e não mexe no ciclo.</p>
        </div>
        <Sparkles aria-hidden="true" size={35} strokeWidth={1.5} />
      </section>

      <section className={styles.missionControls} aria-label="Configurar missão">
        <div className={styles.controlGroup}>
          <span>Ambiente</span>
          <div className={styles.choiceGroup}>
            {environments.map((item) => (
              <button
                aria-pressed={environment === item}
                className={environment === item ? styles.choiceActive : styles.choice}
                key={item}
                onClick={() => setEnvironment(item)}
                type="button"
              >
                {item}
              </button>
            ))}
          </div>
        </div>
        <div className={styles.controlGroup}>
          <span>Duração</span>
          <div className={styles.choiceGroup}>
            {studies.missions.durationOptions.map((item) => (
              <button
                aria-pressed={duration === item}
                className={duration === item ? styles.choiceActive : styles.choice}
                key={item}
                onClick={() => setDuration(item)}
                type="button"
              >
                {item}h
              </button>
            ))}
          </div>
        </div>
        <button className={styles.drawButton} onClick={() => setSeed((value) => value + 1)} type="button">
          <Shuffle aria-hidden="true" size={17} />
          Sortear missão
        </button>
      </section>

      <div className={styles.missionGrid}>
        <section className={styles.section}>
          <div className={styles.sectionHeading}>
            <div>
              <h2>Missão sugerida</h2>
              <p>{mission.length ? `${plannedHours}h ${plannedHours === 1 ? "distribuída" : "distribuídas"}` : "Escolha as opções e faça um sorteio"}</p>
            </div>
          </div>
          <div className={styles.missionResult}>
            {mission.length ? mission.map((item) => (
              <article className={styles.missionRow} key={item.id}>
                <div><strong>{item.subject}</strong><span>Sessão de foco</span></div>
                <strong>{item.hours}h</strong>
              </article>
            )) : <p className={styles.empty}>Nenhuma missão sorteada ainda.</p>}
          </div>
        </section>

        <aside className={styles.availabilityPanel}>
          <div className={styles.sectionHeading}>
            <div>
              <h2>Horas disponíveis</h2>
              <p>{visibleSubjects.length} {visibleSubjects.length === 1 ? "matéria" : "matérias"} neste ambiente</p>
            </div>
          </div>
          <div className={styles.availabilityList}>
            {visibleSubjects.length ? visibleSubjects.map((item) => (
              <div key={item.id}><span>{item.subject}</span><strong>{item.remainingHours}h</strong></div>
            )) : <p className={styles.empty}>Não há horas neste ambiente.</p>}
          </div>
          <div className={styles.localNote}><Clock3 aria-hidden="true" size={15} /><span>A sugestão serve para organizar a próxima sessão.</span></div>
        </aside>
      </div>
    </div>
  );
}
