import { auth }    from "@/lib/auth";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { Sidebar }  from "@/components/layout/Sidebar";
import { TopBar }   from "@/components/layout/TopBar";
import { ToastProvider } from "@/components/ui/Toast";
import { AdjudicationSocketProvider } from "@/components/providers/AdjudicationSocketProvider";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session     = await auth();
  if (!session) redirect("/login");

  const cookieStore  = await cookies();
  const initialPinned = cookieStore.get("sidebar-pinned")?.value === "true";

  return (
    <ToastProvider>
      <AdjudicationSocketProvider>
        <div className="flex h-screen w-screen overflow-hidden bg-background">
          <Sidebar initialPinned={initialPinned} />
          <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
            <TopBar />
            <main
              className="flex-1 overflow-y-auto p-6"
              id="main-content"
            >
              {children}
            </main>
          </div>
        </div>
      </AdjudicationSocketProvider>
    </ToastProvider>
  );
}