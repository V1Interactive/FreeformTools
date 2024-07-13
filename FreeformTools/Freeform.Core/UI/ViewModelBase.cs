/*
 * Freeform Rigging and Animation Tools
 * Copyright (C) 2020  Micah Zahm
 *
 * Freeform Rigging and Animation Tools is free software: you can redistribute it 
 * and/or modify it under the terms of the GNU General Public License as published 
 * by the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * Freeform Rigging and Animation Tools is distributed in the hope that it will 
 * be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with Freeform Rigging and Animation Tools.  
 * If not, see <https://www.gnu.org/licenses/>.
 */

namespace Freeform.Core.UI
{
    using System;
    using System.ComponentModel;
    using System.Diagnostics;
    using System.Linq;

    public class ViewModelBase : INotifyPropertyChanged
    {
        public Action CloseAction { get; set; }
        public event EventHandler CloseWindowEventHandler;

        //basic ViewModelBase
        protected internal void RaisePropertyChanged(string prop)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(prop));
        }
        public event PropertyChangedEventHandler PropertyChanged;

        public void Close()
        {
            // Kill any pythonw programs that are running without a UI (Should only be the process left behind from closing this UI)
            var processes = Process.GetProcesses().Where(pr => pr.MainWindowHandle == IntPtr.Zero);
            foreach (Process proc in processes)
                if (proc.ProcessName == "pythonw")
                    proc.Kill();

            CloseWindowEventHandler?.Invoke(this, null);
            CloseAction();
        }
    }
}
