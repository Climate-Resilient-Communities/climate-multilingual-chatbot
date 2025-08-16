import * as React from 'react';

import {cn} from '@/lib/utils';
import { Slot } from '@radix-ui/react-slot';

const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.ComponentProps<'textarea'> & { as?: React.ElementType; minRows?: number }
>(({className, as, ...props}, ref) => {
  const Comp = as || 'textarea';
  return (
    <Comp
      className={cn(
        'flex min-h-[40px] w-full rounded-md border border-input bg-background px-3 py-2 text-base ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 sm:text-sm',
        className
      )}
      ref={ref}
      {...props}
    />
  );
});
Textarea.displayName = 'Textarea';

export {Textarea};
