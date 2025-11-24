using System;
using System.Collections.Generic;
using System.Linq;

namespace SequenceSolverFixed
{
    class Program
    {
        static void Main(string[] args)
        {
            Console.OutputEncoding = System.Text.Encoding.UTF8;
            Console.WriteLine("Генерация гарантированно разрешимых последовательностей...\n");

            // Тест 1: Короткая последовательность
            RunGuaranteedTest(testId: 1, n: 4, startS: 10, maxStep: 4);

            // Тест 2: Длинная последовательность с большими шагами
            RunGuaranteedTest(testId: 2, n: 10, startS: -50, maxStep: 10);

            // Тест 3: "Плоская" последовательность (шаги 0)
            RunGuaranteedTest(testId: 3, n: 6, startS: 100, maxStep: 0);
            
            Console.WriteLine("\nНажмите любую клавишу для выхода...");
            Console.ReadKey();
        }

        static void RunGuaranteedTest(int testId, int n, int startS, int maxStep)
        {
            Console.WriteLine($"--- ТЕСТ #{testId} ---");

            // 1. Генерируем ИСХОДНУЮ S (Source S), чтобы гарантировать существование решения
            // Важно: Чтобы M были целыми, все элементы S должны иметь одинаковую четность.
            // Поэтому мы прибавляем к S только четные числа.
            int[] sourceS = GenerateValidS(n + 1, startS, maxStep);
            
            // 2. Вычисляем M на основе sourceS
            int[] M = CalculateM(sourceS);

            Console.WriteLine("Дано M (средние значения):");
            Console.WriteLine($"[{string.Join(", ", M)}]");

            // 3. Пытаемся восстановить ВСЕ возможные S, зная только M
            // Диапазон поиска S1 берем с запасом вокруг исходного S[0], так как мы его знаем
            // но в реальной задаче это был бы просто широкий перебор.
            int searchRadius = 500;
            int minSearch = sourceS[0] - searchRadius;
            int maxSearch = sourceS[0] + searchRadius;

            List<int[]> foundSequences = FindAllValidSequences(M, minSearch, maxSearch);

            // 4. Анализ результатов
            int count = foundSequences.Count;
            // k - это параметр из задачи (количество решений = k + 1)
            int k = count > 0 ? count - 1 : 0;

            Console.WriteLine($"\nНайдено возможных последовательностей S: {count}");
            Console.WriteLine($"Параметр k: {k}");

            if (count > 0)
            {
                Console.WriteLine($"\nДиапазон первых элементов S1: от {foundSequences.First()[0]} до {foundSequences.Last()[0]}");
                
                Console.WriteLine("\nПримеры найденных S:");
                // Выводим минимальное решение
                Console.WriteLine($"Min (S1={foundSequences.First()[0]}): [{string.Join(", ", foundSequences.First())}]");
                
                // Если есть, выводим решение, которое совпадает с исходным (для проверки)
                var originalMatch = foundSequences.FirstOrDefault(s => s.SequenceEqual(sourceS));
                if (originalMatch != null)
                {
                    Console.WriteLine($"Src (S1={originalMatch[0]}): [{string.Join(", ", originalMatch)}]  <-- Исходная");
                }

                // Выводим максимальное решение
                if (count > 1)
                {
                    Console.WriteLine($"Max (S1={foundSequences.Last()[0]}): [{string.Join(", ", foundSequences.Last())}]");
                }
            }
            else
            {
                Console.WriteLine("ОШИБКА: Решения не найдены (невозможно при методе обратной генерации).");
            }
            Console.WriteLine(new string('-', 40));
            Console.WriteLine();
        }

        // --- ГЕНЕРАТОРЫ И ЛОГИКА ---

        /// <summary>
        /// Генерирует валидную S: неубывающую, одной четности.
        /// </summary>
        static int[] GenerateValidS(int length, int startValue, int maxStepEven)
        {
            Random rnd = new Random();
            int[] s = new int[length];
            s[0] = startValue;

            for (int i = 1; i < length; i++)
            {
                // Генерируем случайный ЧЕТНЫЙ шаг (0, 2, 4...), 
                // чтобы сохранить четность всей последовательности.
                // Если четность разная, M не будут целыми числами.
                int step = rnd.Next(0, (maxStepEven / 2) + 1) * 2; 
                s[i] = s[i - 1] + step;
            }
            return s;
        }

        static int[] CalculateM(int[] S)
        {
            int[] m = new int[S.Length - 1];
            for (int i = 0; i < m.Length; i++)
            {
                // M[i] = (S[i] + S[i+1]) / 2
                m[i] = (S[i] + S[i + 1]) / 2;
            }
            return m;
        }

        // --- РЕШАТЕЛЬ (SOLVER) ---

        static int[] TryRestoreS(int[] M, int s1)
        {
            int n = M.Length;
            int[] S = new int[n + 1];
            S[0] = s1;

            for (int i = 0; i < n; i++)
            {
                // Si+1 = 2*Mi - Si
                S[i + 1] = 2 * M[i] - S[i];

                // Проверка неубывания: Si <= Si+1
                if (S[i + 1] < S[i])
                {
                    return null; 
                }
            }
            return S;
        }

        static List<int[]> FindAllValidSequences(int[] M, int searchMin, int searchMax)
        {
            var results = new List<int[]>();
            for (int s1 = searchMin; s1 <= searchMax; s1++)
            {
                int[] s = TryRestoreS(M, s1);
                if (s != null)
                {
                    results.Add(s);
                }
            }
            return results;
        }
    }
}
