import {
  ArrowRight,
  BookOpen,
  CalendarClock,
  Check,
  Circle,
  Clock3,
  Dumbbell,
  Flame,
  Target,
} from "lucide-react";

import {
  deadlineLabel,
  formatDatePtBr,
  ratio,
  type DashboardResult,
} from "@/lib/dashboard";
import styles from "./today-dashboard.module.css";

type TodayDashboardProps = DashboardResult;

function SectionTitle({ title, meta }: { title: string; meta?: string }) {
  return (
    <div className={styles.sectionHeading}>
      <h2>{title}</h2>
      {meta ? <span>{meta}</span> : null}
    </div>
  );
}

function ProgressLine({ value }: { value: number }) {
  return (
    <div
      aria-label={`${Math.round(value * 100)}% concluído`}
      aria-valuemax={100}
      aria-valuemin={0}
      aria-valuenow={Math.round(value * 100)}
      className={styles.progressTrack}
      role="progressbar"
    >
      <span style={{ width: `${value * 100}%` }} />
    </div>
  );
}

function heatClass(minutes: number): string {
  if (minutes <= 0) return styles.heat0;
  if (minutes < 45) return styles.heat1;
  if (minutes < 90) return styles.heat2;
  if (minutes < 140) return styles.heat3;
  return styles.heat4;
}

function weekday(value: string): string {
  return new Intl.DateTimeFormat("pt-BR", { weekday: "short" })
    .format(new Date(`${value}T12:00:00`))
    .replace(".", "");
}

export function TodayDashboard({ dashboard, source }: TodayDashboardProps) {
  const questionsProgress = ratio(
    dashboard.weeklyQuestions.completed,
    dashboard.weeklyQuestions.target,
  );
  const questionPercent = Math.round(questionsProgress * 100);
  const remainingQuestions = Math.max(
    dashboard.weeklyQuestions.target - dashboard.weeklyQuestions.completed,
    0,
  );
  const weeklyDifference =
    dashboard.weeklyQuestions.completed - dashboard.weeklyQuestions.previousWeek;
  const readingProgress = dashboard.reading
    ? ratio(dashboard.reading.currentPage, dashboard.reading.totalPages)
    : 0;
  const completedHabits = dashboard.habits.filter((habit) => habit.completed).length;
  const dayName = new Intl.DateTimeFormat("pt-BR", { weekday: "long" }).format(
    new Date(`${dashboard.date}T12:00:00`),
  );

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.dayName}>{dayName}</p>
          <h1>Hoje</h1>
          <p className={styles.date}>{formatDatePtBr(dashboard.date)}</p>
        </div>
        <span className={source === "api" ? styles.liveBadge : styles.demoBadge}>
          <span aria-hidden="true" />
          {source === "api" ? "Dados conectados" : "Dados de demonstração"}
        </span>
      </header>

      <section className={styles.headlineGrid} aria-label="Resumo do dia">
        <article className={styles.focusCard}>
          <div className={styles.focusTopline}>
            <span>{dashboard.focus?.eyebrow ?? "Dia livre"}</span>
            {dashboard.focus ? (
              <span className={styles.duration}>
                <Clock3 aria-hidden="true" size={14} />
                {dashboard.focus.durationMinutes} min
              </span>
            ) : null}
          </div>
          <div className={styles.focusBody}>
            <h2>{dashboard.focus?.title ?? "Nenhuma sessão pendente"}</h2>
            <p>
              {dashboard.focus?.detail ??
                "Use o planejamento para escolher o próximo bloco de estudo."}
            </p>
          </div>
          <a className={styles.focusAction} href="#plano-do-dia">
            Ver plano do dia
            <ArrowRight aria-hidden="true" size={16} />
          </a>
        </article>

        <article className={styles.goalCard}>
          <div className={styles.goalRing}>
            <svg aria-hidden="true" viewBox="0 0 48 48">
              <circle className={styles.goalRingTrack} cx="24" cy="24" r="19" />
              <circle
                className={styles.goalRingValue}
                cx="24"
                cy="24"
                pathLength="100"
                r="19"
                strokeDasharray={`${questionPercent} 100`}
              />
            </svg>
            <strong>{questionPercent}%</strong>
          </div>
          <div className={styles.goalCopy}>
            <span>Questões da semana</span>
            <strong>
              {dashboard.weeklyQuestions.completed} de {dashboard.weeklyQuestions.target}
            </strong>
            <p>
              {remainingQuestions === 0
                ? "Meta concluída."
                : `Faltam ${remainingQuestions} questões.`}
            </p>
            <small>
              {weeklyDifference >= 0 ? "+" : ""}
              {weeklyDifference} em relação à semana anterior
            </small>
          </div>
        </article>
      </section>

      <section className={styles.signalStrip} aria-label="Indicadores principais">
        <div className={styles.streakSignal}>
          <div className={styles.signalValue}>
            <Flame aria-hidden="true" size={18} />
            <strong>{dashboard.user.streakDays} dias</strong>
          </div>
          <span>Sequência atual · recorde de {dashboard.user.longestStreak}</span>
          <div className={styles.heatmap} aria-label="Atividade dos últimos sete dias">
            {dashboard.activity.map((day) => (
              <div className={styles.heatDay} key={day.date}>
                <span
                  aria-label={`${formatDatePtBr(day.date)}: ${day.minutes} minutos`}
                  className={heatClass(day.minutes)}
                  role="img"
                />
                <small>{weekday(day.date)}</small>
              </div>
            ))}
          </div>
        </div>

        <div className={styles.signalDivider} />

        <div className={styles.compactSignal}>
          <span>XP total</span>
          <strong>{dashboard.user.xp.toLocaleString("pt-BR")}</strong>
          <small>Nível {dashboard.user.level}</small>
        </div>

        <div className={styles.signalDivider} />

        <div className={styles.deadlineSignal}>
          <span>{dashboard.deadline?.kind ?? "Próximo prazo"}</span>
          <strong>{dashboard.deadline?.title ?? "Nenhum prazo cadastrado"}</strong>
          {dashboard.deadline ? (
            <small>
              {dashboard.deadline.subject} · {deadlineLabel(dashboard.deadline.date, dashboard.date)}
            </small>
          ) : null}
        </div>
      </section>

      <div className={styles.contentGrid} id="plano-do-dia">
        <div className={styles.primaryColumn}>
          <section className={styles.section}>
            <SectionTitle title="Revisões" meta={`${dashboard.reviews.length} pendentes`} />
            <div className={styles.listPanel}>
              {dashboard.reviews.length ? (
                dashboard.reviews.map((review) => (
                  <div className={styles.listRow} key={review.id}>
                    <span className={styles.rowIcon}>
                      <Target aria-hidden="true" size={16} />
                    </span>
                    <div className={styles.rowMain}>
                      <strong>{review.subject}</strong>
                      <span>{review.topic}</span>
                    </div>
                    <span className={styles.statusChip}>Hoje</span>
                  </div>
                ))
              ) : (
                <p className={styles.emptyCopy}>Nenhuma revisão para hoje.</p>
              )}
            </div>
          </section>

          <section className={styles.section}>
            <SectionTitle
              meta={`${dashboard.priorities.filter((task) => task.completed).length}/${dashboard.priorities.length}`}
              title="Prioridades"
            />
            <div className={styles.listPanel}>
              {dashboard.priorities.length ? (
                dashboard.priorities.map((task) => (
                  <div className={styles.listRow} key={task.id}>
                    <span className={task.completed ? styles.checkDone : styles.checkOpen}>
                      {task.completed ? (
                        <Check aria-hidden="true" size={14} strokeWidth={2.4} />
                      ) : (
                        <Circle aria-hidden="true" size={14} />
                      )}
                    </span>
                    <div className={styles.rowMain}>
                      <strong className={task.completed ? styles.completedText : undefined}>
                        {task.title}
                      </strong>
                      <span>{task.category}</span>
                    </div>
                  </div>
                ))
              ) : (
                <p className={styles.emptyCopy}>Sem prioridades para hoje.</p>
              )}
            </div>
          </section>

          <section className={styles.section}>
            <SectionTitle title="Agenda" />
            <div className={styles.timelinePanel}>
              {dashboard.agenda.length ? (
                dashboard.agenda.map((item) => (
                  <div className={styles.timelineRow} key={item.id}>
                    <time>{item.time}</time>
                    <span className={styles.timelineMarker} />
                    <div>
                      <strong>{item.title}</strong>
                      <span>{item.category}</span>
                    </div>
                  </div>
                ))
              ) : (
                <p className={styles.emptyCopy}>Agenda livre hoje.</p>
              )}
            </div>
          </section>
        </div>

        <aside className={styles.secondaryColumn}>
          <section className={styles.sideSection}>
            <SectionTitle title="Amanhã" />
            <div className={styles.sidePanel}>
              {dashboard.tomorrow.length ? (
                dashboard.tomorrow.map((task) => (
                  <div className={styles.sideRow} key={task.id}>
                    <span>{task.title}</span>
                    <ArrowRight aria-hidden="true" size={15} />
                  </div>
                ))
              ) : (
                <p className={styles.emptyCopy}>Sem prioridades definidas.</p>
              )}
            </div>
          </section>

          <section className={styles.sideSection}>
            <SectionTitle title="Leitura" />
            {dashboard.reading ? (
              <div className={styles.readingPanel}>
                <div className={styles.sidePanelTopline}>
                  <BookOpen aria-hidden="true" size={17} />
                  <span>Em andamento</span>
                </div>
                <strong>{dashboard.reading.title}</strong>
                <p>{dashboard.reading.author}</p>
                <ProgressLine value={readingProgress} />
                <div className={styles.readingMeta}>
                  <span>
                    Página {dashboard.reading.currentPage} de {dashboard.reading.totalPages}
                  </span>
                  <span>Meta: {dashboard.reading.dailyTarget}</span>
                </div>
              </div>
            ) : (
              <div className={styles.sidePanel}>
                <p className={styles.emptyCopy}>Nenhuma leitura em andamento.</p>
              </div>
            )}
          </section>

          <section className={styles.sideSection}>
            <SectionTitle title="Hábitos e atividade" />
            <div className={styles.habitsPanel}>
              <div className={styles.habitsSummary}>
                <span>Hábitos</span>
                <strong>
                  {completedHabits}/{dashboard.habits.length}
                </strong>
              </div>
              <ProgressLine value={ratio(completedHabits, dashboard.habits.length)} />
              <div className={styles.habitList}>
                {dashboard.habits.map((habit) => (
                  <span key={habit.id}>
                    {habit.completed ? (
                      <Check aria-hidden="true" size={13} />
                    ) : (
                      <Circle aria-hidden="true" size={13} />
                    )}
                    {habit.title}
                  </span>
                ))}
              </div>
              <div className={styles.activityRow}>
                <Dumbbell aria-hidden="true" size={17} />
                <div>
                  <strong>{dashboard.physicalActivity ?? "Sem treino registrado"}</strong>
                  <span>Atividade física</span>
                </div>
              </div>
            </div>
          </section>
        </aside>
      </div>

      <footer className={styles.footerNote}>
        <CalendarClock aria-hidden="true" size={14} />
        <span>Primeira etapa da nova interface. Nenhuma escrita é enviada ao Google Sheets.</span>
      </footer>
    </div>
  );
}
