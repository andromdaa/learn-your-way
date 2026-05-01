import { createRootRoute, Link, Outlet } from "@tanstack/react-router";

export const Route = createRootRoute({
  component: RootLayout,
});

function RootLayout() {
  return (
    <div style={{ display: "flex", minHeight: "100vh", fontFamily: "system-ui, sans-serif" }}>
      <nav
        style={{
          width: 200,
          background: "#1a1a2e",
          color: "#eee",
          padding: "1rem",
          display: "flex",
          flexDirection: "column",
          gap: "0.5rem",
        }}
      >
        <div style={{ fontWeight: "bold", marginBottom: "1rem", fontSize: "1.1rem" }}>
          Learn Your Way
        </div>
        <NavLink to="/">Dashboard</NavLink>
        <NavLink to="/sources">Sources</NavLink>
        <NavLink to="/lessons">Lessons</NavLink>
        <NavLink to="/profiles">Profiles</NavLink>
        <NavLink to="/jobs">Jobs</NavLink>
        <NavLink to="/health">Health</NavLink>
      </nav>
      <main style={{ flex: 1, padding: "1.5rem", overflow: "auto" }}>
        <Outlet />
      </main>
    </div>
  );
}

function NavLink({ to, children }: { to: string; children: React.ReactNode }) {
  return (
    <Link
      to={to}
      style={{ color: "#aaa", textDecoration: "none", padding: "0.25rem 0" }}
      activeProps={{ style: { color: "#fff", fontWeight: "bold" } }}
    >
      {children}
    </Link>
  );
}
