export const metadata = { title: "Jarvis" };
import "./globals.css";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="sv">
      <body className="min-h-screen bg-gray-950 text-gray-50">{children}</body>
    </html>
  );
}


