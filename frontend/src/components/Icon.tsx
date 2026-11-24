import type { ReactNode } from 'react';

export function Icon({ name, size = 20 }: {
  name: string;
  size?: number
}) {
  const paths: Record<string, ReactNode> = {
    board: <>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M7 8h10M7 12h10M7 16h6" />
    </>,
    briefcase: <>
      <rect x="3" y="7" width="18" height="13" rx="2" />
      <path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 12h18M10 12v2h4v-2" />
    </>,
    bell: <>
      <path d="M18 8a6 6 0 0 0-12 0c0 7-2 7-2 9h16c0-2-2-2-2-9M10 20h4" />
    </>,
    clock: <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>,
    alert: <>
      <path d="M12 3 2.5 20h19L12 3Z" />
      <path d="M12 9v4M12 17h.01" />
    </>,
    calendar: <>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M7 3v4M17 3v4M3 10h18M8 14h3" />
    </>,
    lock: <>
      <rect x="5" y="10" width="14" height="11" rx="2" />
      <path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3" />
    </>,
    arrow: <>
      <path d="M5 12h14M14 7l5 5-5 5" />
    </>,
    plus: <path d="M12 5v14M5 12h14" />,
    file: <>
      <path d="M6 3h8l4 4v14H6zM14 3v5h4M9 13h6M9 17h6" />
    </>,
    trash: <>
      <path d="M4 7h16M9 7V4h6v3M7 7l1 13h8l1-13M10 11v5M14 11v5" />
    </>,
    check: <path d="m5 12 4 4L19 6" />,
  };
  return <svg
    aria-hidden="true"
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.7"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    {paths[name]}
  </svg>;
}
