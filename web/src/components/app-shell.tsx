import type { ReactNode } from "react";
import type { Route } from "next";
import Link from "next/link";
import {
  Award,
  BookOpen,
  CalendarDays,
  ChartNoAxesCombined,
  CheckSquare2,
  CircleGauge,
  Dumbbell,
  ListTodo,
  NotebookTabs,
  Settings,
  Sparkles,
  Target,
  type LucideIcon,
} from "lucide-react";

import type { DashboardUser } from "@/lib/dashboard";
import { ratio } from "@/lib/dashboard";
import styles from "./app-shell.module.css";

export type AppPath =
  | "/"
  | "/planejar"
  | "/rotina"
  | "/ciclo"
  | "/missoes"
  | "/leitura"
  | "/tarefas"
  | "/habitos"
  | "/atividade"
  | "/progresso"
  | "/conquistas"
  | "/configuracoes"
  | "/mais";

type NavigationItem = {
  label: string;
  icon: LucideIcon;
  href: Route;
};

const navigation: NavigationItem[] = [
  { label: "Hoje", icon: CircleGauge, href: "/" },
  { label: "Planejar", icon: CalendarDays, href: "/planejar" },
  { label: "Rotina", icon: NotebookTabs, href: "/rotina" },
  { label: "Ciclo", icon: Target, href: "/ciclo" },
  { label: "Missões", icon: Sparkles, href: "/missoes" },
  { label: "Leitura", icon: BookOpen, href: "/leitura" },
  { label: "Tarefas", icon: CheckSquare2, href: "/tarefas" },
  { label: "Hábitos", icon: ListTodo, href: "/habitos" },
  { label: "Atividade", icon: Dumbbell, href: "/atividade" },
  { label: "Progresso", icon: ChartNoAxesCombined, href: "/progresso" },
  { label: "Conquistas", icon: Award, href: "/conquistas" },
  { label: "Configurações", icon: Settings, href: "/configuracoes" },
];

const mobileNavigation = navigation.filter(({ label }) =>
  ["Hoje", "Planejar", "Rotina", "Progresso"].includes(label),
);

type AppShellProps = {
  children: ReactNode;
  currentPath: AppPath;
  user: DashboardUser;
};

export function AppShell({ children, currentPath, user }: AppShellProps) {
  const levelProgress = ratio(user.xpInLevel, user.xpPerLevel);

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <span className={styles.brandMark}>N</span>
          <span className={styles.brandName}>NEXO</span>
        </div>

        <section className={styles.levelCard} aria-label="Progresso de nível">
          <div className={styles.levelRow}>
            <strong>Nível {user.level}</strong>
            <span>{user.xp.toLocaleString("pt-BR")} XP</span>
          </div>
          <div className={styles.levelTrack} aria-hidden="true">
            <span style={{ width: `${levelProgress * 100}%` }} />
          </div>
          <small>
            {user.xpToNextLevel.toLocaleString("pt-BR")} XP para o próximo nível
          </small>
        </section>

        <nav className={styles.navigation} aria-label="Navegação principal">
          {navigation.map(({ label, icon: Icon, href }) => {
            const active = href === currentPath;
            return (
              <Link
                aria-current={active ? "page" : undefined}
                className={active ? styles.navItemActive : styles.navItem}
                href={href}
                key={label}
              >
                <Icon aria-hidden="true" size={17} strokeWidth={1.8} />
                <span>{label}</span>
              </Link>
            );
          })}
        </nav>
      </aside>

      <main className={styles.main}>{children}</main>

      <nav className={styles.mobileNav} aria-label="Navegação móvel">
        {mobileNavigation.map(({ label, icon: Icon, href }) => {
          const active = href === currentPath;
          return (
            <Link
              aria-current={active ? "page" : undefined}
              className={active ? styles.mobileItemActive : styles.mobileItem}
              href={href}
              key={label}
            >
              <Icon aria-hidden="true" size={20} strokeWidth={1.8} />
              <span>{label}</span>
            </Link>
          );
        })}
        <Link
          aria-current={!mobileNavigation.some(({ href }) => href === currentPath) ? "page" : undefined}
          className={
            !mobileNavigation.some(({ href }) => href === currentPath)
              ? styles.mobileItemActive
              : styles.mobileItem
          }
          href="/mais"
        >
          <Settings aria-hidden="true" size={20} strokeWidth={1.8} />
          <span>Mais</span>
        </Link>
      </nav>
    </div>
  );
}
