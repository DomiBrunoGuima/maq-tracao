/** O backend grava created_at em UTC sem fuso ("2026-10-19T21:00:00"); sem o "Z"
 *  o navegador leria como hora local e mostraria 3 h a mais no Brasil. */
export function dataUTC(iso: string): Date {
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`);
}
