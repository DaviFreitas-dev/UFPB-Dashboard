import Link from "next/link";
import {
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  Check,
  Circle,
  Clock3,
  ListChecks,
  NotebookTabs,
} from "lucide-react";

import { formatDatePtBr, ratio } from "@/lib/dashboard";
import { addRoutineDays, type RoutineResult } from "@/lib/routine";
import {
  RoutineControls,
  RoutineCreateForm,
} from "./personal-actions/routine-controls";
import styles from "./routine-dashboard.module.css";

function weekday(value: string): string {
  const date = new Date(`${value}T12:00:00`);
  if (Number.isNaN(date.getTime())) return "Dia selecionado";

  const label = new Intl.DateTimeFormat("pt-BR", { weekday: "long" }).format(date);
  return label.charAt(0).toUpperCase() + label.slice(1);
}

type RoutineDashboardProps = RoutineResult & {
  canMutate: boolean;
  initialItemId: string;
};

export function RoutineDashboard({
  routine,
  source,
  canMutate,
  initialItemId,
}: RoutineDashboardProps) {
  const previousDate = addRoutineDays(routine.date, -1);
  const nextDate = addRoutineDays(routine.date, 1);
  const progress = ratio(routine.completed, routine.total);
  const progressPercent = Math.round(progress * 100);
  const nextItem = routine.items.find((item) => !item.completed) ?? null;
  const remaining = Math.max(routine.total - routine.completed, 0);

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>{weekday(routine.date)}</p>
          <h1>Rotina</h1>
          <p className={styles.intro}>Seu dia, em ordem.</p>
        </div>
        <span className={source === "api" ? styles.liveBadge : styles.demoBadge}>
          <span aria-hidden="true" />
          {source === "api" ? "Dados conectados" : "Demonstração"}
        </span>
      </header>

      <nav className={styles.dateNavigation} aria-label="Escolher dia da rotina">
        <Link
          aria-label="Dia anterior"
          className={styles.dateArrow}
          href={{ pathname: "/rotina", query: { date: previousDate } }}
        >
          <ArrowLeft aria-hidden="true" size={16} />
        </Link>
        <div>
          <CalendarDays aria-hidden="true" size={17} />
          <strong>{formatDatePtBr(routine.date)}</strong>
        </div>
        <Link className={styles.todayLink} href="/rotina">
          Hoje
        </Link>
        <Link
          aria-label="Próximo dia"
          className={styles.dateArrow}
          href={{ pathname: "/rotina", query: { date: nextDate } }}
        >
          <ArrowRight aria-hidden="true" size={16} />
        </Link>
      </nav>

      <section className={styles.heroGrid} aria-label="Resumo da rotina">
        <article className={styles.progressCard}>
          <div className={styles.progressRing}>
            <svg aria-hidden="true" viewBox="0 0 48 48">
              <circle className={styles.ringTrack} cx="24" cy="24" r="19" />
              <circle
                className={styles.ringValue}
                cx="24"
                cy="24"
                pathLength="100"
                r="19"
                strokeDasharray={`${progressPercent} 100`}
              />
            </svg>
            <strong>{progressPercent}%</strong>
          </div>
          <div>
            <span>Progresso do dia</span>
            <strong>
              {routine.completed} de {routine.total} concluídas
            </strong>
            <p>
              {routine.total === 0
                ? "Nada marcado para este dia."
                : remaining === 0
                  ? "Dia concluído."
                  : `${remaining} ${remaining === 1 ? "atividade restante" : "atividades restantes"}.`}
            </p>
          </div>
        </article>

        <article className={styles.nextCard}>
          <div className={styles.nextTopline}>
            <span>{nextItem ? "Próximo compromisso" : "Situação do dia"}</span>
            <Clock3 aria-hidden="true" size={16} />
          </div>
          <strong>{nextItem?.title ?? (routine.total ? "Tudo concluído" : "Agenda livre")}</strong>
          <p>
            {nextItem
              ? `${nextItem.time} · ${nextItem.category}`
              : routine.total
                ? "Tudo certo por aqui."
                : "Aproveite o espaço ou planeje com calma."}
          </p>
        </article>
      </section>

      {canMutate ? (
        <RoutineCreateForm
          initialItemId={initialItemId}
          selectedDate={routine.date}
        />
      ) : source === "api" ? (
        <p className={styles.writesUnavailable}>
          As alterações ainda não estão disponíveis nesta versão.
        </p>
      ) : null}

      <div className={styles.contentGrid}>
        <section className={styles.timelineSection}>
          <div className={styles.sectionHeading}>
            <h2>Linha do tempo</h2>
            <span>{routine.total} itens</span>
          </div>

          <div className={styles.timelinePanel}>
            {routine.items.length ? (
              routine.items.map((item) => (
                <article className={item.completed ? styles.timelineDone : styles.timelineRow} key={item.id}>
                  <time>{item.time}</time>
                  <div className={styles.timelineTrack} aria-hidden="true">
                    <span className={item.completed ? styles.markerDone : styles.markerOpen}>
                      {item.completed ? <Check size={12} /> : <Circle size={10} />}
                    </span>
                  </div>
                  <div className={styles.timelineCopy}>
                    <div>
                      <strong>{item.title}</strong>
                      {item.completed ? <span className={styles.doneLabel}>Concluído</span> : null}
                    </div>
                    <p>
                      {item.category}
                      <span>·</span>
                      {item.kind === "fixed" ? "Semana fixa" : "Compromisso avulso"}
                    </p>
                    <RoutineControls
                      canMutate={source === "api" && canMutate}
                      item={item}
                    />
                  </div>
                </article>
              ))
            ) : (
              <div className={styles.emptyTimeline}>
                <CalendarDays aria-hidden="true" size={20} />
                <strong>Dia livre</strong>
                <span>Nenhum horário ou compromisso cadastrado.</span>
              </div>
            )}
          </div>
        </section>

        <aside className={styles.sideColumn}>
          <section className={styles.sideSection}>
            <div className={styles.sectionHeading}>
              <h2>Composição do dia</h2>
            </div>
            <div className={styles.sidePanel}>
              <div className={styles.metricRow}>
                <span className={styles.metricIcon}>
                  <NotebookTabs aria-hidden="true" size={16} />
                </span>
                <div>
                  <span>Semana fixa</span>
                  <strong>{routine.fixedCount}</strong>
                </div>
              </div>
              <div className={styles.metricRow}>
                <span className={styles.metricIcon}>
                  <ListChecks aria-hidden="true" size={16} />
                </span>
                <div>
                  <span>Avulsos</span>
                  <strong>{routine.customCount}</strong>
                </div>
              </div>
            </div>
          </section>

          <section className={styles.sideSection}>
            <div className={styles.sectionHeading}>
              <h2>Ritmo do dia</h2>
            </div>
            <div className={styles.rhythmPanel}>
              <span>{remaining === 0 && routine.total ? "Fechado" : "Em andamento"}</span>
              <strong>
                {routine.total === 0
                  ? "Sem pressão hoje"
                  : remaining === 0
                    ? "Agenda cumprida"
                    : nextItem?.time === "--:--"
                      ? "Próximo item sem horário"
                      : `Próximo às ${nextItem?.time}`}
              </strong>
              <p>
                {routine.total === 0
                  ? "O dia está aberto para descanso ou encaixes."
                  : remaining === 0
                    ? "Todas as atividades registradas foram concluídas."
                    : "Concentre-se apenas no próximo compromisso."}
              </p>
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}
