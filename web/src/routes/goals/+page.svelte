<script lang="ts">
  import Card from '$lib/components/Card.svelte'
  import Button from '$lib/components/Button.svelte'
  import Modal from '$lib/components/Modal.svelte'
  import GoalForm from '$lib/components/GoalForm.svelte'
  import Badge from '$lib/components/Badge.svelte'
  import { currentPortfolio } from '$lib/stores'
  import { api } from '$lib/api/client'
  import { formatCurrency, formatDate, getMonthsFromNow } from '$lib/utils/format'
  import { onMount } from 'svelte'

  let loading = true
  let goals: any[] = []
  let showNewModal = false

  onMount(async () => {
    if ($currentPortfolio) await loadGoals()
  })

  $: if ($currentPortfolio) loadGoals()

  async function loadGoals() {
    try {
      loading = true
      const [data, portfolioData] = await Promise.all([
        api.get(`/goals`, { portfolio_id: $currentPortfolio.id }),
        api.get(`/portfolios/${$currentPortfolio.id}`)
      ])
      const currentValue = portfolioData?.current_value || '0'
      goals = (data || []).map((g: any) => ({ ...g, current_value: currentValue }))
    } catch (e) {
      console.error('Failed to load goals:', e)
    } finally {
      loading = false
    }
  }

  async function handleCreateGoal(goal: any) {
    try {
      await api.post(`/portfolios/${$currentPortfolio.id}/goals`, goal)
      await loadGoals()
      showNewModal = false
    } catch (e) {
      console.error('Failed to create goal:', e)
    }
  }

  async function handleDeleteGoal(id: string) {
    if (!confirm('Delete this goal?')) return
    try {
      await api.delete(`/goals/${id}`)
      await loadGoals()
    } catch (e) {
      console.error('Failed to delete goal:', e)
    }
  }

  function getGoalStatus(goal: any): 'on_track' | 'behind' | 'ahead' {
    const monthsLeft = getMonthsFromNow(goal.target_date)
    const progressPercent = (goal.current_value / goal.target_amount) * 100
    const expectedPercent = Math.max(0, 100 - (monthsLeft / (getMonthsFromNow(goal.target_date) + 12)) * 100)

    if (progressPercent >= expectedPercent) return 'ahead'
    if (progressPercent >= expectedPercent * 0.8) return 'on_track'
    return 'behind'
  }

  function getStatusBadge(status: string): 'default' | 'secondary' | 'destructive' {
    switch (status) {
      case 'ahead':
        return 'secondary'
      case 'on_track':
        return 'default'
      default:
        return 'destructive'
    }
  }
</script>

<div class="min-h-screen bg-background p-4 md:p-6">
  <div class="mx-auto max-w-6xl space-y-6">
    <!-- Header -->
    <div class="flex flex-col gap-4 sm:gap-6 sm:items-start sm:justify-between md:flex-row md:items-center">
      <div class="space-y-2">
        <h1 class="text-2xl md:text-3xl font-bold text-foreground">Goals</h1>
        <p class="text-xs md:text-sm text-muted-foreground">Track financial goals and FIRE projections</p>
      </div>
      <Button variant="default" on:click={() => (showNewModal = true)} class="w-full sm:w-auto">
        <svg class="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        New Goal
      </Button>
    </div>

    {#if loading}
      <div class="flex justify-center py-12">
        <div class="text-muted-foreground">Loading goals...</div>
      </div>
    {:else if goals.length === 0}
      <Card title="No goals yet" subtitle="Create a goal to track your financial targets">
        <div class="py-8 text-center">
          <p class="mb-4 text-muted-foreground">
            Set investment goals and track your progress towards financial milestones.
          </p>
          <Button variant="default" on:click={() => (showNewModal = true)}>
            Create First Goal
          </Button>
        </div>
      </Card>
    {:else}
      <div class="space-y-4">
        {#each goals as goal}
          {@const status = getGoalStatus(goal)}
          {@const progressPercent = Math.min(100, (goal.current_value / goal.target_amount) * 100)}
          <Card title={goal.name} subtitle={goal.description || formatDate(goal.target_date)}>
            <div class="space-y-4">
              <div class="space-y-2">
                <div class="flex justify-between">
                  <span class="text-xs md:text-sm text-muted-foreground">Target</span>
                  <span class="text-sm md:text-base font-semibold text-foreground">
                    {formatCurrency(goal.target_amount)}
                  </span>
                </div>
                <div class="flex justify-between">
                  <span class="text-xs md:text-sm text-muted-foreground">Current</span>
                  <span class="text-sm md:text-base font-semibold text-foreground">
                    {formatCurrency(goal.current_value)}
                  </span>
                </div>
              </div>

              <!-- Progress Bar -->
              <div class="space-y-1">
                <div class="flex justify-between items-center">
                  <span class="text-xs text-muted-foreground">Progress</span>
                  <Badge variant={getStatusBadge(status)}>
                    {status.replace('_', ' ').toUpperCase()}
                  </Badge>
                </div>
                <div class="w-full bg-muted rounded-full h-2">
                  <div
                    class="bg-accent h-2 rounded-full transition-all"
                    style="width: {progressPercent}%"
                  />
                </div>
                <div class="text-xs text-muted-foreground">
                  {progressPercent.toFixed(1)}% of target
                </div>
              </div>

              <div class="flex gap-2 pt-4">
                <Button variant="outline" size="sm" href="/goals/{goal.id}">
                  Edit
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  on:click={() => handleDeleteGoal(goal.id)}
                >
                  Delete
                </Button>
              </div>
            </div>
          </Card>
        {/each}
      </div>
    {/if}
  </div>
</div>

<Modal
  open={showNewModal}
  title="Create Goal"
  onClose={() => (showNewModal = false)}
>
  <GoalForm
    onSubmit={handleCreateGoal}
    goal={{
      name: '',
      target_amount: '',
      target_date: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      expected_annual_return: '0.07',
      description: ''
    }}
  />
  <svelte:fragment slot="footer">
    <Button variant="outline" on:click={() => (showNewModal = false)}>
      Cancel
    </Button>
  </svelte:fragment>
</Modal>
