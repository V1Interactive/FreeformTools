namespace Freeform.Rigging.CharacterPicker
{
    using System;
    using System.ComponentModel;
    using System.Diagnostics;
    using System.Windows;
    using System.Windows.Interop;

    using Freeform.Core.UI;

    /// <summary>
    /// Interaction logic for CharacterPicker.xaml
    /// </summary>
    public partial class CharacterPicker : Window
    {
        public CharacterPicker()
        {
            InitializeComponent();
            SetupDataContext();
        }

        public CharacterPicker(Process parent)
        {
            InitializeComponent();

            WindowInteropHelper helper = new WindowInteropHelper(this);
            helper.Owner = parent.MainWindowHandle;

            SetupDataContext();
        }

        void SetupDataContext()
        {
            CharacterPickerVM vm = new CharacterPickerVM();
            DataContext = vm;
            if (vm.CloseAction == null)
            {
                vm.CloseAction = new Action(Close);
            }
        }

        protected override void OnClosed(EventArgs e)
        {
            base.OnClosed(e);
            CharacterPickerVM vm = DataContext as CharacterPickerVM;
            vm.Close();
        }
    }
}
