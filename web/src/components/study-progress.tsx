import { BarChart3, BookOpenCheck, CircleCheckBig, Target } from "lucide-react";

import { formatDatePtBr, ratio } from "@/lib/dashboard";
import type { StudyWorkspaceResult } from "@/lib/study-workspace";
import styles from "./study-workspace.module.css";

function percent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function StudyProgress({ studies, source }: StudyWorkspaceResult) {
  const { progress } = studies;
  const historyMax = Math.max(1, ...progress.studyHistory.map((item) => item.hours));
  const totals = [
    { label: "Horas estudadas", value: `${progress.totals.studyHours}h`, icon: BookOpenCheck },
    { label: "Questões", value: progress.totals.questions.toLocaleString("pt-BR"), icon: Target },
    { label: "Aproveitamento", value: percent(progress.totals.accuracy), icon: CircleCheckBig },
    { label: "Sequência", value: `${progress.totals.streakDays} dias`, icon: BarChart3 },
  ];

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>Visão de longo prazo</p>
          <h1>Progresso</h1>
          <p className={styles.intro}>Acompanhe seu desempenho e os assuntos que precisam de revisão.</p>
        </div>
        <div className={styles.headerMeta}>
          <span>{formatDatePtBr(studies.date)}</span>
          <span className={source === "api" ? styles.liveBadge : styles.demoBadge}>
            <span aria-hidden="true" />
            {source === "api" ? "Dados conectados" : "Demonstração"}
          </span>
        </div>
      </header>

      <section className={styles.metricGrid} aria-label="Resumo geral">
        {totals.map(({ label, value, icon: Icon }) => (
          <article className={styles.metricCard} key={label}><Icon aria-hidden="true" size={18} /><span>{label}</span><strong>{value}</strong></article>
        ))}
      </section>

      <section className={styles.weekSummary}>
        <div><span>Esta semana</span><strong>{progress.week.studyHours}h de estudo</strong><p>{formatDatePtBr(progress.week.start)} — {formatDatePtBr(progress.week.end)}</p></div>
        <div className={styles.weekValues}>
          <span><strong>{progress.week.questions}</strong> questões</span><span><strong>{percent(progress.week.accuracy)}</strong> acerto</span><span><strong>{progress.week.tasksCompleted}</strong> tarefas</span><span><strong>{progress.week.reviewsCompleted}</strong> revisões</span>
        </div>
      </section>

      <div className={styles.progressGrid}>
        <section className={styles.section}>
          <div className={styles.sectionHeading}><div><h2>Horas estudadas</h2><p>Últimos registros</p></div></div>
          {progress.studyHistory.length ? <div className={styles.historyChart}>
            {progress.studyHistory.map((item) => <div className={styles.historyItem} key={item.date}><div><span style={{ height: `${ratio(item.hours, historyMax) * 100}%` }} /></div><small>{new Date(`${item.date}T12:00:00`).toLocaleDateString("pt-BR", { weekday: "narrow" })}</small><strong>{item.hours}h</strong></div>)}
          </div> : <p className={styles.empty}>Ainda não há horas registradas.</p>}
        </section>

        <section className={styles.section}>
          <div className={styles.sectionHeading}><div><h2>Acerto semanal</h2><p>Desempenho por semana</p></div></div>
          <div className={styles.trendList}>
            {progress.weeklyAccuracy.length ? progress.weeklyAccuracy.map((item) => <div key={item.weekStart}><span>{new Date(`${item.weekStart}T12:00:00`).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" })}</span><div className={styles.progressTrack} aria-hidden="true"><span style={{ width: `${ratio(item.accuracy, 1) * 100}%` }} /></div><strong>{percent(item.accuracy)}</strong></div>) : <p className={styles.empty}>Ainda não há semanas para comparar.</p>}
          </div>
        </section>
      </div>

      <div className={styles.progressGrid}>
        <section className={styles.section}>
          <div className={styles.sectionHeading}><div><h2>Desempenho por matéria</h2><p>Questões e horas acumuladas</p></div></div>
          <div className={styles.performanceTable}>
            {progress.subjects.length ? progress.subjects.map((item) => <article key={item.subject}><div><strong>{item.subject}</strong><span>{item.questions} questões · {item.studyHours}h</span></div><div className={styles.subjectAccuracy}><span className={styles.progressTrack} aria-hidden="true"><span style={{ width: `${ratio(item.accuracy, 1) * 100}%` }} /></span><strong>{percent(item.accuracy)}</strong></div></article>) : <p className={styles.empty}>O desempenho aparece após a primeira sessão.</p>}
          </div>
        </section>

        <aside className={styles.reviewPanel}>
          <div className={styles.sectionHeading}><div><h2>Pontos para revisar</h2><p>Erros ainda abertos</p></div></div>
          {progress.reviewPoints.length ? <div className={styles.reviewList}>{progress.reviewPoints.map((item) => <article key={`${item.subject}-${item.topic}`}><div><strong>{item.subject}</strong><span>{item.topic}</span></div><b>{item.quantity}</b></article>)}</div> : <p className={styles.empty}>Nenhum ponto pendente.</p>}
        </aside>
      </div>
    </div>
  );
}
