import {
  BookText,
  CalendarRange,
  Check,
  ChevronRight,
  Circle,
  Clock3,
  NotebookPen,
  Target,
  TriangleAlert,
} from "lucide-react";

import { deadlineLabel, formatDatePtBr, ratio } from "@/lib/dashboard";
import type { PlanningResult } from "@/lib/planning";
import styles from "./planning-dashboard.module.css";

function compactDate(value: string): string {
  const date = new Date(`${value}T12:00:00`);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
  })
    .format(date)
    .replace(".", "");
}

function SectionHeading({ title, count }: { title: string; count?: number }) {
  return (
    <div className={styles.sectionHeading}>
      <h2>{title}</h2>
      {typeof count === "number" ? <span>{count}</span> : null}
    </div>
  );
}

export function PlanningDashboard({ planning, source }: PlanningResult) {
  const questionProgress = ratio(
    planning.weeklyQuestions.completed,
    planning.weeklyQuestions.target,
  );
  const remainingQuestions = Math.max(
    planning.weeklyQuestions.target - planning.weeklyQuestions.completed,
    0,
  );

  const summary = [
    { label: "Horas estudadas", value: `${planning.summary.studyHours.toLocaleString("pt-BR")}h` },
    { label: "Questões", value: planning.summary.questions.toLocaleString("pt-BR") },
    { label: "Aproveitamento", value: `${Math.round(planning.summary.accuracy * 100)}%` },
    { label: "Tarefas concluídas", value: planning.summary.tasksCompleted.toLocaleString("pt-BR") },
    { label: "Revisões feitas", value: planning.summary.reviewsCompleted.toLocaleString("pt-BR") },
  ];

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>Semana atual</p>
          <h1>Planejar</h1>
          <p className={styles.intro}>A semana inteira, sem perder de vista o que vence primeiro.</p>
        </div>
        <div className={styles.headerMeta}>
          <span>{formatDatePtBr(planning.summary.start)} — {formatDatePtBr(planning.summary.end)}</span>
          <span className={source === "api" ? styles.liveBadge : styles.demoBadge}>
            <span aria-hidden="true" />
            {source === "api" ? "Dados conectados" : "Demonstração"}
          </span>
        </div>
      </header>

      <section className={styles.summaryStrip} aria-label="Resumo da semana">
        {summary.map((item) => (
          <div className={styles.summaryItem} key={item.label}>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </div>
        ))}
      </section>

      <section className={styles.weekSection}>
        <div className={styles.weekTopline}>
          <SectionHeading title="Calendário semanal" />
          <div className={styles.goalCompact}>
            <span>Meta de questões</span>
            <strong>
              {planning.weeklyQuestions.completed} / {planning.weeklyQuestions.target}
            </strong>
            <div className={styles.progressTrack} aria-hidden="true">
              <span style={{ width: `${questionProgress * 100}%` }} />
            </div>
            <small>
              {remainingQuestions ? `Faltam ${remainingQuestions}` : "Meta concluída"}
            </small>
          </div>
        </div>

        <div className={styles.weekBoard}>
          {planning.week.map((day) => (
            <article className={day.isToday ? styles.dayToday : styles.day} key={day.date}>
              <header>
                <span>{day.name.slice(0, 3)}</span>
                <strong>{compactDate(day.date)}</strong>
              </header>
              <div className={styles.dayItems}>
                {day.items.length ? (
                  day.items.map((item) => (
                    <div className={styles.dayItem} key={item.id}>
                      <time>{item.time}</time>
                      <strong>{item.title}</strong>
                      <span>{item.category}</span>
                    </div>
                  ))
                ) : (
                  <span className={styles.freeDay}>Livre</span>
                )}
              </div>
            </article>
          ))}
        </div>
      </section>

      <div className={styles.mainGrid}>
        <div className={styles.primaryColumn}>
          <section className={styles.section}>
            <SectionHeading count={planning.assessments.length} title="Prazos" />
            <div className={styles.panel}>
              {planning.assessments.length ? (
                planning.assessments.map((assessment) => (
                  <div className={assessment.isBoss ? styles.bossRow : styles.deadlineRow} key={assessment.id}>
                    <span className={styles.rowIcon}>
                      {assessment.isBoss ? (
                        <Target aria-hidden="true" size={17} />
                      ) : (
                        <CalendarRange aria-hidden="true" size={17} />
                      )}
                    </span>
                    <div className={styles.rowCopy}>
                      <span>{assessment.isBoss ? "BOSS" : assessment.kind}</span>
                      <strong>{assessment.title}</strong>
                      <small>
                        {assessment.subject} · {deadlineLabel(assessment.date, planning.date)}
                        {assessment.questionGoal ? ` · meta de ${assessment.questionGoal} questões` : ""}
                      </small>
                    </div>
                    <time>{compactDate(assessment.date)}</time>
                  </div>
                ))
              ) : (
                <p className={styles.empty}>Nenhum prazo aberto.</p>
              )}
            </div>
          </section>

          <section className={styles.section}>
            <SectionHeading count={planning.reviews.length} title="Revisões pendentes" />
            <div className={styles.panel}>
              {planning.reviews.length ? (
                planning.reviews.map((review) => (
                  <div className={styles.reviewRow} key={review.id}>
                    <span className={styles.rowIcon}>
                      <Clock3 aria-hidden="true" size={16} />
                    </span>
                    <div className={styles.rowCopy}>
                      <strong>{review.subject}</strong>
                      <small>{review.topic}</small>
                    </div>
                    <span className={styles.dueChip}>
                      {deadlineLabel(review.dueDate, planning.date)}
                    </span>
                  </div>
                ))
              ) : (
                <p className={styles.empty}>Revisões em dia.</p>
              )}
            </div>
          </section>
        </div>

        <aside className={styles.secondaryColumn}>
          <section className={styles.section}>
            <SectionHeading count={planning.weakPoints.length} title="Pontos fracos" />
            <div className={styles.sidePanel}>
              {planning.weakPoints.length ? (
                planning.weakPoints.map((item) => (
                  <div className={styles.weakRow} key={item.id}>
                    <TriangleAlert aria-hidden="true" size={16} />
                    <div>
                      <strong>{item.subject} · {item.topic}</strong>
                      <span>
                        {item.quantity} {item.quantity === 1 ? "erro" : "erros"}
                        {item.note ? ` · ${item.note}` : ""}
                      </span>
                    </div>
                  </div>
                ))
              ) : (
                <p className={styles.empty}>Nenhum ponto fraco aberto.</p>
              )}
            </div>
          </section>

          <section className={styles.section}>
            <SectionHeading count={planning.tomorrow.length} title="Amanhã" />
            <div className={styles.sidePanel}>
              {planning.tomorrow.length ? (
                planning.tomorrow.map((item) => (
                  <div className={styles.tomorrowRow} key={item.id}>
                    <span className={item.completed ? styles.checkDone : styles.checkOpen}>
                      {item.completed ? <Check aria-hidden="true" size={13} /> : <Circle aria-hidden="true" size={13} />}
                    </span>
                    <strong>{item.title}</strong>
                    <ChevronRight aria-hidden="true" size={15} />
                  </div>
                ))
              ) : (
                <p className={styles.empty}>Amanhã ainda está livre.</p>
              )}
            </div>
          </section>

          <section className={styles.section}>
            <SectionHeading title="Diário recente" />
            <div className={styles.journalPanel}>
              {planning.journal.length ? (
                planning.journal.map((entry) => (
                  <article className={styles.journalEntry} key={entry.id}>
                    <div>
                      <NotebookPen aria-hidden="true" size={15} />
                      <time>{formatDatePtBr(entry.date)}</time>
                    </div>
                    <p>{entry.text}</p>
                  </article>
                ))
              ) : (
                <div className={styles.emptyJournal}>
                  <BookText aria-hidden="true" size={18} />
                  <span>Nenhuma nota recente.</span>
                </div>
              )}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
