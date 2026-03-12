export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <main className="min-h-screen w-full flex items-center justify-center bg-background">
      {children}
    </main>
  );
}