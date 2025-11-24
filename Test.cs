using System;
using System.Collections.Generic;
using System.Linq;

namespace SequenceSolver
{
    class Program
    {
        static void Main(string[] args)
        {
            Console.OutputEncoding = System.Text.Encoding.UTF8;
            
            // Запускаем несколько тестов для проверки
            RunTest(testId: 1, n: 4, rangeMin: 0, rangeMax: 10);
            RunTest(testId: 2, n: 5, rangeMin: 10, rangeMax: 30);
            RunTest(testId: 3, n: 6, rangeMin: -10, rangeMax: 10);
            
            Console.WriteLine("\nНажмите любую клавишу для выхода...");
            Console.ReadKey();
        }

        static void RunTest(int testId, int n, int rangeMin, int rangeMax)
        {
            Console.WriteLine($"\n--- ТЕСТ #{testId} ---");

            // 1. Генерируем случайную неубывающую последовательность M
            int[] M = GenerateSortedM(n, rangeMin, rangeMax);
            Console.WriteLine($"Сгенерированная последовательность M ({M.Length} элементов):");
            Console.WriteLine(string.Join(", ", M));

            // 2. Находим все возможные последовательности S
            // Для поиска границ перебора используем эвристику:
            // S1 не может быть сильно больше M[0] (так как S1 <= M1)
            // и не может быть бесконечно малым. 
            // Возьмем широкий диапазон вокруг M[0] для демонстрации.
            int searchRadius = 1000; 
            int startSearch = M[0] - searchRadius;
            int endSearch = M[0] + searchRadius;

            List<int[]> validSequences = FindAllValidSequences(M, startSearch, endSearch);

            // 3. Вывод результатов
            int count = validSequences.Count;
            int k = count > 0 ? count - 1 : 0;

            if (count > 0)
            {
                Console.WriteLine($"\nНайдено валидных последовательностей S: {count}");
                Console.WriteLine($"Следовательно, значение k = {k} (так как решений k+1).");
                
                Console.WriteLine("\nПримеры найденных последовательностей S (первые 3 и последние 3):");
                PrintSamples(validSequences);
                
                // Проверка граничных значений S1
                int minS1 = validSequences.First()[0];
                int maxS1 = validSequences.Last()[0];
                Console.WriteLine($"\nДиапазон допустимых значений S1: [{minS1}; {maxS1}]");
            }
            else
            {
                Console.WriteLine("\nВалидных последовательностей не найдено в заданном диапазоне поиска.");
            }
        }

        // --- ФУНКЦИИ ---

        /// <summary>
        /// Генерирует неубывающую последовательность целых чисел M длины n
        /// </summary>
        static int[] GenerateSortedM(int n, int min, int max)
        {
            Random rnd = new Random();
            int[] m = new int[n];
            for (int i = 0; i < n; i++)
            {
                m[i] = rnd.Next(min, max + 1);
            }
            Array.Sort(m); // Гарантируем неубывание
            return m;
        }

        /// <summary>
        /// Восстанавливает S по M и заданному начальному элементу s1.
        /// Возвращает null, если полученная последовательность не является неубывающей.
        /// </summary>
        static int[] TryRestoreS(int[] M, int s1)
        {
            int n = M.Length;
            int[] S = new int[n + 1];
            S[0] = s1;

            for (int i = 0; i < n; i++)
            {
                // Формула: Mi = (Si + Si+1) / 2  =>  2*Mi = Si + Si+1  =>  Si+1 = 2*Mi - Si
                S[i + 1] = 2 * M[i] - S[i];

                // Проверка условия неубывания на лету
                if (S[i + 1] < S[i])
                {
                    return null; // Последовательность нарушила условие
                }
            }

            return S;
        }

        /// <summary>
        /// Перебирает варианты S1 и находит все валидные последовательности
        /// </summary>
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

        static void PrintSamples(List<int[]> seqs)
        {
            int total = seqs.Count;
            if (total <= 6)
            {
                foreach (var s in seqs) Console.WriteLine($"S1={s[0]}: [{string.Join(", ", s)}]");
            }
            else
            {
                for (int i = 0; i < 3; i++) 
                    Console.WriteLine($"S1={seqs[i][0]}: [{string.Join(", ", seqs[i])}]");
                Console.WriteLine("...");
                for (int i = total - 3; i < total; i++) 
                    Console.WriteLine($"S1={seqs[i][0]}: [{string.Join(", ", seqs[i])}]");
            }
        }
    }
}
