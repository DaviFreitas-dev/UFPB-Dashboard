export default function Loading() {
  return (
    <main
      aria-label="Carregando painel"
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        color: "#969daa",
        background: "#0d0f12",
        fontSize: ".78rem",
      }}
    >
      Carregando dados do dia…
    </main>
  );
}
