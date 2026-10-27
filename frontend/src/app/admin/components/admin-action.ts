import { css } from "lit";
export const adminActionStyles = css`
  button[appAdminAction] {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-height: 27px;
    padding: 0 11px;
    color: var(--admin-text-soft);
    font-size: 0.7rem;
    font-weight: 600;
    background: var(--admin-raised);
    border: 1px solid var(--admin-line-strong);
    border-radius: 8px;
    cursor: pointer;
    transition:
      color 130ms ease,
      background-color 130ms ease,
      border-color 130ms ease;
  }
  button[appAdminAction]:hover:not(:disabled) {
    color: var(--admin-text);
    background: var(--admin-hover);
    border-color: var(--admin-line-bright);
  }
  button[appAdminAction]:disabled {
    color: var(--admin-text-faint);
    cursor: default;
  }
  button[appAdminAction]:focus-visible {
    outline: 2px solid var(--admin-focus);
    outline-offset: 1px;
  }
  button[appAdminAction][data-tone="danger"] {
    color: var(--admin-bad);
    border-color: rgb(203 105 98 / 30%);
  }
  button[appAdminAction][data-tone="danger"]:hover:not(:disabled) {
    color: #f4dcd8;
    background: rgb(203 105 98 / 16%);
    border-color: rgb(203 105 98 / 48%);
  }
  @media (prefers-reduced-motion: reduce) {
    button[appAdminAction] {
      transition: none;
    }
  }
`;
