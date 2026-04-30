'use client'

import React from 'react'
import { PricingTable } from '@clerk/nextjs'

type BoundaryState = { hasError: boolean }

/**
 * PricingTable depends on Clerk Billing being configured.
 * If it throws (missing products, etc.), we fall back to a minimal message instead of crashing the route.
 */
export class PricingTableBoundary extends React.Component<
  React.PropsWithChildren,
  BoundaryState
> {
  declare state: BoundaryState

  constructor(props: React.PropsWithChildren) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(): BoundaryState {
    return { hasError: true }
  }

  componentDidCatch(error: Error) {
    console.error('[PricingTable]', error)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="mx-auto max-w-lg rounded-xl border border-amber-200 bg-amber-50 p-6 text-center text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100">
          <p className="font-medium">Pricing could not be loaded.</p>
          <p className="mt-2 text-sm opacity-90">
            Ensure Clerk Billing and products are configured in the Clerk Dashboard, then redeploy.
          </p>
        </div>
      )
    }

    return <PricingTable />
  }
}
