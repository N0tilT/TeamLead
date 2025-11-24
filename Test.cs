using System;
using System.Collections.Generic;
using System.Linq;

namespace SequenceHypothesisCheck
{
    class Program
    {
        static void Main(string[] args)
        {
            Console.OutputEncoding = System.Text.Encoding.UTF8;
            Console.WriteLine("=== ПРОВЕРКА ГИПОТЕЗЫ О ЧИСЛЕ K ===\n");
            Console.WriteLine("Формула из картинки: k = min(M[i] - M[i-1])");
            Console.WriteLine("Ожидаемое число решений: k + 1\n");

            // Запускаем серию тестов
            RunTest(1, n: 5, startS: 0, stepBase: 4);
            RunTest(2, n: 8, startS: 100, stepBase: 10);
            RunTest(3, n: 4, startS: -50, stepBase: 20);
            
            // Тест на "плотную" последовательность (маленькая разница между M)
            RunTest(4, n: 6, startS: 10, stepBase: 2); 

            Console.WriteLine("\nНажмите любую клавишу для завершения...");
            Console.ReadKey();
        }

        static void RunTest(int testId, int n, int startS, int stepBase)
        {
            Console.WriteLine($"--- ТЕСТ #{testId} ---");

            // 1. Генерация валидной последовательности M
            // Мы генерируем исходную S, чтобы гарантировать, что хотя бы одно решение существует,
            // и чтобы M была неубывающей (важно для условия задачи).
            int[] sourceS = GenerateConvexS(n + 1, startS, stepBase);
            int[] M = CalculateM(sourceS);

            Console.WriteLine($"Последовательность M ({M.Length} эл.): [{string.Join(", ", M)}]");

            // 2. Вычисление теоретического K по формуле из картинки
            // k = min( m_i - m_{i-1} )
            int? k_theoretical = CalculateKFromImage(M);

            if (k_theoretical == null)
            {
                Console.WriteLine("Невозможно вычислить k (слишком короткая последовательность).");
                return;
            }

            int expectedCount = k_theoretical.Value + 1;

            // 3. Поиск фактического количества решений (Brute Force)
            // Ищем S1 в широком диапазоне
            int searchRange = 2000; 
            int minSearch = sourceS[0] - searchRange;
            int maxSearch = sourceS[0] + searchRange;

            List<int[]> solutions = FindAllValidSequences(M, minSearch, maxSearch);
            int actualCount = solutions.Count;

            // 4. Сравнение и вывод
            Console.WriteLine($"\nРасчет по формуле (k): {k_theoretical}");
            Console.WriteLine($"Предсказанное кол-во (k+1): {expectedCount}");
            Console.WriteLine($"Фактически найдено решений: {actualCount}");

            if (expectedCount == actualCount)
            {
                Console.ForegroundColor = ConsoleColor.Green;
                Console.WriteLine("РЕЗУЛЬТАТ: СОВПАДАЕТ [OK]");
            }
            else
            {
                Console.ForegroundColor = ConsoleColor.Red;
                Console.WriteLine("РЕЗУЛЬТАТ: ОШИБКА [FAIL]");
            }
            Console.ResetColor();
            
            if (actualCount > 0)
            {
                // Показать диапазон S1 для наглядности
                int minS1 = solutions.First()[0];
                int maxS1 = solutions.Last()[0];
                Console.WriteLine($"Диапазон S1: [{minS1} ... {maxS1}] (Длина диапазона: {maxS1 - minS1 + 1})");
            }
            Console.WriteLine();
        }

        // --- ЛОГИКА ВЫЧИСЛЕНИЯ K (ИЗ КАРТИНКИ) ---
        static int? CalculateKFromImage(int[] M)
        {
            if (M.Length < 2) return null;

            int minDiff = int.MaxValue;
            
            // Проходим по M и ищем минимальную разницу между соседями
            // 2 <= i <= n (в 1-based индексе), что соответствует 1..Length-1 в 0-based
            for (int i = 1; i < M.Length; i++)
            {
                int diff = M[i] - M[i - 1];
                if (diff < minDiff)
                {
                    minDiff = diff;
                }
            }
            return minDiff;
        }

        // --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

        // Генерирует S так, чтобы M была неубывающей.
        // Для этого S должна быть "выпуклой" или линейно растущей с достаточным шагом.
        static int[] GenerateConvexS(int length, int start, int stepBase)
        {
            Random rnd = new Random();
            int[] s = new int[length];
            s[0] = start;
            
            // Текущий шаг между элементами S
            int currentStep = stepBase; 

            for (int i = 1; i < length; i++)
            {
                // Чтобы M росла, расстояние между элементами S должно примерно сохраняться или расти.
                // Добавляем случайную четную добавку к шагу.
                int stepDelta = rnd.Next(0, 3) * 2; 
                currentStep += stepDelta; 
                
                s[i] = s[i - 1] + currentStep;
            }
            return s;
        }

        static int[] CalculateM(int[] S)
        {
            int[] m = new int[S.Length - 1];
            for (int i = 0; i < m.Length; i++)
            {
                m[i] = (S[i] + S[i + 1]) / 2;
            }
            return m;
        }

        static List<int[]> FindAllValidSequences(int[] M, int minSearch, int maxSearch)
        {
            var results = new List<int[]>();
            for (int s1 = minSearch; s1 <= maxSearch; s1++)
            {
                int[] s = TryRestoreS(M, s1);
                if (s != null)
                {
                    results.Add(s);
                }
            }
            return results;
        }

        static int[] TryRestoreS(int[] M, int s1)
        {
            int n = M.Length;
            int[] S = new int[n + 1];
            S[0] = s1;

            for (int i = 0; i < n; i++)
            {
                // S[i+1] = 2*M[i] - S[i]
                long nextVal = 2L * M[i] - S[i]; // используем long во избежание переполнения на шаге
                
                if (nextVal > int.MaxValue || nextVal < int.MinValue) return null;
                
                S[i + 1] = (int)nextVal;

                // Условие неубывания: Si <= Si+1
                if (S[i + 1] < S[i]) return null;
            }
            return S;
        }
    }
}
