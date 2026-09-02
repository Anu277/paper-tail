import { GripVertical } from "lucide-react";
import { Group, Panel, Separator } from "react-resizable-panels";

import { cn } from "@/lib/utils";

// NOTE: this file targets react-resizable-panels v4, which renamed Group's
// `direction` prop to `orientation` and no longer emits a
// `data-panel-group-direction` DOM attribute at all (it emits `data-group`/
// `data-panel`/`data-separator` instead, with no orientation info) — so
// direction-dependent styling below is computed from the `direction` prop
// directly in JS rather than via `data-[panel-group-direction=...]` CSS
// selectors, which would silently never match against this version.
const ResizablePanelGroup = ({
  className,
  direction = "horizontal",
  ...props
}: Omit<React.ComponentProps<typeof Group>, "orientation"> & {
  direction?: "horizontal" | "vertical";
}) => (
  <Group
    orientation={direction}
    className={cn(
      "flex h-full w-full",
      direction === "vertical" && "flex-col",
      className,
    )}
    {...props}
  />
);

const ResizablePanel = Panel;

const ResizableHandle = ({
  withHandle,
  className,
  direction = "horizontal",
  ...props
}: React.ComponentProps<typeof Separator> & {
  withHandle?: boolean;
  direction?: "horizontal" | "vertical";
}) => (
  <Separator
    className={cn(
      "relative flex items-center justify-center bg-border focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring focus-visible:ring-offset-1",
      direction === "vertical"
        ? "h-px w-full after:absolute after:inset-x-0 after:top-1/2 after:h-1 after:-translate-y-1/2"
        : "w-px after:absolute after:inset-y-0 after:left-1/2 after:w-1 after:-translate-x-1/2",
      className,
    )}
    {...props}
  >
    {withHandle && (
      <div
        className={cn(
          "z-10 flex items-center justify-center rounded-sm border bg-border",
          direction === "vertical" ? "h-3 w-4" : "h-4 w-3",
        )}
      >
        <GripVertical
          className={cn("h-2.5 w-2.5", direction === "vertical" && "rotate-90")}
        />
      </div>
    )}
  </Separator>
);

export { ResizablePanelGroup, ResizablePanel, ResizableHandle };
