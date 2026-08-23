import Link from "next/link";
import { ArrowLeft, ArrowRight, CalendarDays } from "lucide-react";
import type { ReactNode } from "react";

import { formatDatePtBr } from "@/lib/dashboard";
import { addRoutineDays } from "@/lib/routine";
import styles from "./personal-workspace.module.css";

type PersonalWorkspaceRoute = "/tarefas" | "/habitos" | "/leitura" | "/atividade";

type PersonalWorkspaceFrameProps = {
  title: string;
  intro: string;
  date: string;
  source: "api" | "demo";
  route: PersonalWorkspaceRoute;
  showDateNavigation?: boolean;
  children: ReactNode;
};

export function PersonalWorkspaceFrame({
  title,
  intro,
  date,
  source,
  route,
  showDateNavigation = true,
  children,
}: PersonalWorkspaceFrameProps) {
  const previousDate = addRoutineDays(date, -1);
  const nextDate = addRoutineDays(date, 1);

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>Rotina pessoal</p>
          <h1>{title}</h1>
          <p className={styles.intro}>{intro}</p>
        </div>
        <span className={source === "api" ? styles.liveBadge : styles.demoBadge}>
          <span aria-hidden="true" />
          {source === "api" ? "Dados conectados" : "Demonstração"}
        </span>
      </header>

      {showDateNavigation ? (
        <nav className={styles.dateNavigation} aria-label={`Escolher dia de ${title}`}>
          <Link
            aria-label="Dia anterior"
            className={styles.dateArrow}
            href={{ pathname: route, query: { date: previousDate } }}
          >
            <ArrowLeft aria-hidden="true" size={16} />
          </Link>
          <div>
            <CalendarDays aria-hidden="true" size={17} />
            <strong>{formatDatePtBr(date)}</strong>
          </div>
          <Link className={styles.todayLink} href={route}>
            Hoje
          </Link>
          <Link
            aria-label="Próximo dia"
            className={styles.dateArrow}
            href={{ pathname: route, query: { date: nextDate } }}
          >
            <ArrowRight aria-hidden="true" size={16} />
          </Link>
        </nav>
      ) : null}

      {children}
    </div>
  );
}
