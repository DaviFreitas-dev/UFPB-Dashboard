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

type NavigationItem = {
  label: string;
  icon: LucideIcon;
  href?: Route;
};

const navigation: NavigationItem[] = [
  { label: "Hoje", icon: CircleGauge, href: "/" },
  { label: "Planejar", icon: CalendarDays, href: "/planejar" },
  { label: "Rotina", icon: NotebookTabs, href: "/rotina" },
  { label: "Ciclo", icon: Target },
  { label: "Missões", icon: Sparkles },
  { label: "Leitura", icon: BookOpen },
  { label: "Tarefas", icon: CheckSquare2 },
  { label: "Hábitos", icon: ListTodo },
  { label: "Atividade", icon: Dumbbell },
  { label: "Progresso", icon: ChartNoAxesCombined },
  { label: "Conquistas", icon: Award },
  { label: "Configurações", icon: Settings },
];

const mobileNavigation = navigation.filter(({ label }) =>
  ["Hoje", "Planejar", "Rotina", "Progresso"].includes(label),
);

type AppShellProps = {
  children: ReactNode;
  currentPath: "/" | "/planejar" | "/rotina";
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

            if (href) {
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
            }

            return (
              <button
                className={styles.navItem}
                disabled
                key={label}
                title="Disponível no NEXO atual"
                type="button"
              >
                <Icon aria-hidden="true" size={17} strokeWidth={1.8} />
                <span>{label}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      <main className={styles.main}>{children}</main>

      <nav className={styles.mobileNav} aria-label="Navegação móvel">
        {mobileNavigation.map(({ label, icon: Icon, href }) => {
          const active = href === currentPath;

          if (href) {
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
          }

          return (
            <button className={styles.mobileItem} disabled key={label} type="button">
              <Icon aria-hidden="true" size={20} strokeWidth={1.8} />
              <span>{label}</span>
            </button>
          );
        })}
        <button className={styles.mobileItem} disabled type="button">
          <Settings aria-hidden="true" size={20} strokeWidth={1.8} />
          <span>Mais</span>
        </button>
      </nav>
    </div>
  );
}
