<script setup></script>

<template>
    <main class="relative flex min-h-screen overflow-hidden">
        <aside
            class="custom-scrollbar relative h-full overflow-x-clip overflow-y-auto rounded-l-3xl border-r bg-gray-50 transition-all duration-400 ease-in-out min-w-64 w-64"
        >
            <ul class="flex min-w-64 flex-col gap-3 p-2">
                <button class="flex items-center gap-2 rounded-lg p-2 hover:bg-gray-100">
                    <div class="rounded-full bg-sky-500 p-1 text-white">
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke-width="1.5"
                            stroke="currentColor"
                            class="size-4"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M12 4.5v15m7.5-7.5h-15"
                            />
                        </svg>
                    </div>
                    <span class="text-sm font-medium">New Chat</span>
                </button>
                <li>
                    <span class="shrink-0 px-2 text-xs text-gray-500">12.01.12</span>
                    <a class="list-item">
                        <div class="group relative w-full cursor-pointer rounded-lg p-2">
                            <span
                                class="mask-linear-gradient block overflow-hidden whitespace-nowrap"
                            >
                                Chat Name
                            </span>

                            <div class="flex">
                                <input
                                    maxlength="30"
                                    class="m-0 w-full rounded-lg border-b border-sky-500 bg-transparent py-0 leading-normal text-inherit outline-none"
                                />
                            </div>
                        </div>
                    </a>
                </li>
            </ul>
        </aside>
        <div>asdfasdf</div>
    </main>
</template>
